import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.delivery.models import NotificationChannel


class NotificationChannelRepository:
    """Repository for notification channels data access.
    Queries only; never commits transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_project(self, project_id: uuid.UUID) -> Sequence[NotificationChannel]:
        """Fetch all notification channels for a project ordered by creation date descending."""
        query = (
            select(NotificationChannel)
            .where(NotificationChannel.project_id == project_id)
            .order_by(NotificationChannel.created_at.desc(), NotificationChannel.id.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, channel: NotificationChannel) -> NotificationChannel:
        """Add and flush a new notification channel."""
        self.session.add(channel)
        await self.session.flush()
        await self.session.refresh(channel)
        return channel
