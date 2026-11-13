import logging
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.uuid7 import uuid7
from app.delivery.models import NotificationChannel
from app.delivery.repository import NotificationChannelRepository
from app.delivery.schemas import NotificationChannelCreate

logger = logging.getLogger(__name__)


class NotificationChannelService:
    """Service owning business rules and transaction boundaries for notification channels."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = NotificationChannelRepository(session)

    async def list_channels(self, project_id: uuid.UUID) -> Sequence[NotificationChannel]:
        """List all notification channels for a project.

        # TODO: verify project belongs to the JWT workspace (Control Plane lookup)
        """
        return await self.repository.list_by_project(project_id)

    async def create_channel(
        self,
        project_id: uuid.UUID,
        channel_in: NotificationChannelCreate,
    ) -> NotificationChannel:
        """Create a new notification channel for a project.

        # TODO: verify project belongs to the JWT workspace (Control Plane lookup)
        """
        channel_id = uuid7()
        channel = NotificationChannel(
            id=channel_id,
            project_id=project_id,
            name=channel_in.name,
            channel_type=channel_in.channel_type,
            destination=channel_in.destination,
            credentials_encrypted=None,
            secret_reference=None,
            enabled=channel_in.enabled,
        )

        created_channel = await self.repository.create(channel)
        await self.session.commit()
        await self.session.refresh(created_channel)

        logger.info(
            "Created notification channel id=%s project_id=%s type=%s",
            channel_id,
            project_id,
            channel_in.channel_type,
        )
        return created_channel
