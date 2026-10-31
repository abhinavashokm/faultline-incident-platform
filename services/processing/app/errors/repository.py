from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.models import ErrorEvent, Issue


class ErrorsRepository:
    """Repository layer for processing.issues and processing.error_events.

    Contains database queries only. Never commits transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
