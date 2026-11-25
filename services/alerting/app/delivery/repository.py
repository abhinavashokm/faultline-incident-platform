import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.delivery.models import NotificationChannel


class NotificationChannelRepository:
    """Repository for notification channels data access.
    Queries only; never commits transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> Sequence[NotificationChannel]:
        """Fetch all notification channels for a project ordered by creation date descending."""
        query = (
            select(NotificationChannel)
            .where(
                NotificationChannel.workspace_id == workspace_id,
                NotificationChannel.project_id == project_id,
            )
            .order_by(NotificationChannel.created_at.desc(), NotificationChannel.id.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    def _channel_scope(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, channel_id: uuid.UUID
    ) -> tuple[ColumnElement[bool], ...]:
        return (
            NotificationChannel.workspace_id == workspace_id,
            NotificationChannel.project_id == project_id,
            NotificationChannel.id == channel_id,
        )

    async def get_by_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, channel_id: uuid.UUID,
        *, for_update: bool = False,
    ) -> NotificationChannel | None:
        query = select(NotificationChannel).where(
            *self._channel_scope(workspace_id, project_id, channel_id)
        )
        if for_update:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def delete_by_project(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, channel_id: uuid.UUID
    ) -> bool:
        deleted_id = await self.session.scalar(
            delete(NotificationChannel)
            .where(*self._channel_scope(workspace_id, project_id, channel_id))
            .returning(NotificationChannel.id)
        )
        return deleted_id is not None

    async def create(self, channel: NotificationChannel) -> NotificationChannel:
        """Add and flush a new notification channel."""
        self.session.add(channel)
        await self.session.flush()
        await self.session.refresh(channel)
        return channel
