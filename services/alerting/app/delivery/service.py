import html
import logging
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.uuid7 import uuid7
from app.delivery.email import EmailSender, mask_email, strip_crlf
from app.delivery.models import NotificationChannel
from app.delivery.repository import NotificationChannelRepository
from app.delivery.schemas import NotificationChannelCreate

logger = logging.getLogger(__name__)


async def _send_channel_confirmation_email_task(
    email_sender: EmailSender,
    channel_id: uuid.UUID,
    destination: str,
    channel_name: str,
    project_id: uuid.UUID,
    created_by: str,
    created_at_utc: str,
    enabled: bool,
) -> None:
    """Background task to send confirmation email. Failures are logged and do not raise."""
    clean_name = strip_crlf(channel_name)
    subject = f'Your Faultline notification channel "{clean_name}" was added'
    status_text = "Enabled" if enabled else "Disabled"

    text_body = (
        f'Faultline Notification Channel Added\n\n'
        f'The notification channel "{clean_name}" has been added to Faultline.\n\n'
        f'Details:\n'
        f'- Channel Name: {clean_name}\n'
        f'- Project ID: {project_id}\n'
        f'- Status: {status_text}\n'
        f'- Created By: {created_by}\n'
        f'- Created At (UTC): {created_at_utc}\n\n'
        f'If you did not expect this, contact your workspace admin.\n'
    )

    escaped_name = html.escape(clean_name)
    escaped_created_by = html.escape(created_by)
    escaped_status = html.escape(status_text)
    html_body = (
        f'<!DOCTYPE html>\n'
        f'<html>\n'
        f'<body>\n'
        f'<h2>Faultline Notification Channel Added</h2>\n'
        f'<p>The notification channel <strong>"{escaped_name}"</strong> has been added to Faultline.</p>\n'
        f'<ul>\n'
        f'  <li><strong>Channel Name:</strong> {escaped_name}</li>\n'
        f'  <li><strong>Project ID:</strong> {project_id}</li>\n'
        f'  <li><strong>Status:</strong> {escaped_status}</li>\n'
        f'  <li><strong>Created By:</strong> {escaped_created_by}</li>\n'
        f'  <li><strong>Created At (UTC):</strong> {created_at_utc}</li>\n'
        f'</ul>\n'
        f'<p><em>If you did not expect this, contact your workspace admin.</em></p>\n'
        f'</body>\n'
        f'</html>'
    )

    try:
        await email_sender.send(
            to_email=destination,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        logger.info(
            "Sent channel confirmation email channel_id=%s destination=%s",
            channel_id,
            mask_email(destination),
        )
    except Exception as exc:
        logger.error(
            "Failed to send confirmation email channel_id=%s destination=%s: %s",
            channel_id,
            mask_email(destination),
            exc,
        )


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
        creator_id: uuid.UUID | None = None,
        background_tasks: BackgroundTasks | None = None,
        email_sender: EmailSender | None = None,
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

        # Trigger confirmation email only AFTER commit for email channels
        if channel_in.channel_type == "email" and background_tasks is not None and email_sender is not None:
            created_at_utc = (
                created_channel.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                if created_channel.created_at
                else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            )
            created_by = str(creator_id) if creator_id else "Unknown"

            background_tasks.add_task(
                _send_channel_confirmation_email_task,
                email_sender=email_sender,
                channel_id=created_channel.id,
                destination=created_channel.destination,
                channel_name=created_channel.name,
                project_id=project_id,
                created_by=created_by,
                created_at_utc=created_at_utc,
                enabled=created_channel.enabled,
            )

        return created_channel
