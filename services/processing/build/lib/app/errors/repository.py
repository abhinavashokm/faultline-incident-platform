from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.models import ErrorEvent, Issue


class ErrorsRepository:
    """Repository layer for processing.issues and processing.error_events.

    Contains database queries only. Never commits transactions.
    Every query enforces workspace_id and project_id isolation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -------------------------------------------------------------------------
    # Consumer & Grouping Operations
    # -------------------------------------------------------------------------

    async def upsert_issue(self, values: dict[str, Any]) -> tuple[UUID, bool]:
        """Upsert the issue on (project_id, fingerprint).

        Performs a no-op update on conflict, returning the issue ID and whether the
        row was newly inserted (is_new).
        """
        stmt = (
            pg_insert(Issue)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["project_id", "fingerprint"],
                set_={"fingerprint": pg_insert(Issue).excluded.fingerprint},
            )
            .returning(Issue.id, text("(xmax = 0) AS is_new"))
        )
        result = await self.session.execute(stmt)
        row = result.one()
        return row[0], bool(row[1])

    async def insert_event(self, values: dict[str, Any]) -> bool:
        """Insert event into processing.error_events.

        Deduplicates on error_events.id. Returns True if inserted, False on conflict.
        """
        stmt = (
            pg_insert(ErrorEvent)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(ErrorEvent.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def bump_issue_counters(
        self,
        issue_id: UUID,
        occurred_at: datetime,
        release: str | None,
    ) -> None:
        """Increment occurrence_count, update first/last seen timestamps and newest release."""
        stmt = (
            update(Issue)
            .where(Issue.id == issue_id)
            .values(
                occurrence_count=Issue.occurrence_count + 1,
                first_seen_at=func.least(Issue.first_seen_at, occurred_at),
                last_seen_at=func.greatest(Issue.last_seen_at, occurred_at),
                last_release=case(
                    (occurred_at >= Issue.last_seen_at, func.coalesce(release, Issue.last_release)),
                    else_=Issue.last_release,
                ),
                updated_at=func.now(),
            )
        )
        await self.session.execute(stmt)

    async def get_issue(self, issue_id: UUID) -> Issue | None:
        stmt = select(Issue).where(Issue.id == issue_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_issue_by_fingerprint(self, project_id: UUID, fingerprint: str) -> Issue | None:
        stmt = select(Issue).where(
            Issue.project_id == project_id,
            Issue.fingerprint == fingerprint,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_event(self, event_id: UUID) -> ErrorEvent | None:
        stmt = select(ErrorEvent).where(ErrorEvent.id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_events_for_issue(self, issue_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ErrorEvent)
            .where(ErrorEvent.issue_id == issue_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    # -------------------------------------------------------------------------
    # HTTP API Tenant-Scoped Queries
    # -------------------------------------------------------------------------

    async def list_issues(
        self,
        workspace_id: UUID,
        project_id: UUID,
        status: str | None,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> list[dict[str, Any]]:
        """List issues ordered by last_seen_at DESC, id DESC with keyset pagination."""
        stmt = (
            select(
                Issue.id,
                Issue.title,
                Issue.status,
                Issue.level,
                Issue.exception_type,
                Issue.culprit,
                Issue.occurrence_count,
                Issue.first_seen_at.label("first_seen"),
                Issue.last_seen_at.label("last_seen"),
                Issue.first_release,
                Issue.last_release,
                Issue.affected_users_count,
            )
            .where(
                Issue.workspace_id == workspace_id,
                Issue.project_id == project_id,
            )
        )
        if status:
            stmt = stmt.where(Issue.status == status)

        if cursor:
            cursor_last_seen, cursor_id = cursor
            stmt = stmt.where(
                or_(
                    Issue.last_seen_at < cursor_last_seen,
                    and_(
                        Issue.last_seen_at == cursor_last_seen,
                        Issue.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(Issue.last_seen_at.desc(), Issue.id.desc()).limit(limit + 1)
        res = await self.session.execute(stmt)
        return [dict(row) for row in res.mappings().all()]

    async def get_issue_detail(
        self,
        workspace_id: UUID,
        project_id: UUID,
        issue_id: UUID,
    ) -> Issue | None:
        """Fetch single issue detail filtered by workspace_id and project_id."""
        stmt = select(Issue).where(
            Issue.workspace_id == workspace_id,
            Issue.project_id == project_id,
            Issue.id == issue_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_events(
        self,
        workspace_id: UUID,
        project_id: UUID,
        issue_id: UUID,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> list[dict[str, Any]]:
        """List events of an issue ordered by occurred_at DESC, id DESC with keyset pagination."""
        stmt = (
            select(
                ErrorEvent.id,
                ErrorEvent.issue_id,
                ErrorEvent.occurred_at,
                ErrorEvent.received_at,
                ErrorEvent.level,
                ErrorEvent.exception_type,
                ErrorEvent.message,
                ErrorEvent.environment,
                ErrorEvent.release,
                ErrorEvent.event_type,
            )
            .where(
                ErrorEvent.workspace_id == workspace_id,
                ErrorEvent.project_id == project_id,
                ErrorEvent.issue_id == issue_id,
            )
        )

        if cursor:
            cursor_occurred_at, cursor_id = cursor
            stmt = stmt.where(
                or_(
                    ErrorEvent.occurred_at < cursor_occurred_at,
                    and_(
                        ErrorEvent.occurred_at == cursor_occurred_at,
                        ErrorEvent.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(ErrorEvent.occurred_at.desc(), ErrorEvent.id.desc()).limit(limit + 1)
        res = await self.session.execute(stmt)
        return [dict(row) for row in res.mappings().all()]

    async def get_event_detail(
        self,
        workspace_id: UUID,
        project_id: UUID,
        issue_id: UUID,
        event_id: UUID,
    ) -> ErrorEvent | None:
        """Fetch single event detail filtered by workspace_id, project_id, and issue_id."""
        stmt = select(ErrorEvent).where(
            ErrorEvent.workspace_id == workspace_id,
            ErrorEvent.project_id == project_id,
            ErrorEvent.issue_id == issue_id,
            ErrorEvent.id == event_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def update_issue_status(
        self,
        workspace_id: UUID,
        project_id: UUID,
        issue_id: UUID,
        new_status: str,
        resolved_in_release: str | None,
        user_id: UUID,
    ) -> Issue | None:
        """Atomically update status, keeping updated columns strictly disjoint from consumer writes."""
        now_utc = datetime.now(timezone.utc)
        stmt = (
            update(Issue)
            .where(
                Issue.workspace_id == workspace_id,
                Issue.project_id == project_id,
                Issue.id == issue_id,
            )
            .values(
                status=new_status,
                resolved_at=case(
                    (Issue.status == new_status, Issue.resolved_at),
                    (new_status == "resolved", now_utc),
                    else_=None,
                ),
                resolved_by=case(
                    (Issue.status == new_status, Issue.resolved_by),
                    (new_status == "resolved", user_id),
                    else_=None,
                ),
                resolved_in_release=case(
                    (Issue.status == new_status, Issue.resolved_in_release),
                    (new_status == "resolved", resolved_in_release),
                    else_=None,
                ),
                updated_at=case(
                    (Issue.status == new_status, Issue.updated_at),
                    else_=now_utc,
                ),
            )
            .returning(Issue)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
