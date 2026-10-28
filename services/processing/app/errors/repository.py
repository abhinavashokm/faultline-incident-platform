from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.models import ErrorEvent, Issue


class ErrorsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_issue(self, values: dict[str, Any]) -> UUID:
        stmt = (
            pg_insert(Issue)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["project_id", "fingerprint"],
                set_={"fingerprint": pg_insert(Issue).excluded.fingerprint},
            )
            .returning(Issue.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def insert_event(self, values: dict[str, Any]) -> bool:
        stmt = (
            pg_insert(ErrorEvent)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(ErrorEvent.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def bump_issue_counters(
        self, issue_id: UUID, occurred_at: datetime, release: str | None
    ) -> None:
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

