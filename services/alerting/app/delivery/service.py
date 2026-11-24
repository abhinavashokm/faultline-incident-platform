import html
import json
import logging
import secrets
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.uuid7 import uuid7
from app.delivery.email import EmailDeliveryError, EmailSender, mask_email, strip_crlf
from app.delivery.models import NotificationChannel
from app.delivery.repository import NotificationChannelRepository
from app.delivery.schemas import (
    HeaderWebhookAuth,
    NotificationChannelCreate,
    WebhookChannelCreate,
    WebhookChannelCreated,
)
from app.delivery.webhook import WebhookChannelSender, WebhookDeliveryError

logger = logging.getLogger(__name__)


def _serialize_webhook_auth(channel_in: WebhookChannelCreate) -> dict[str, str] | None:
    auth = channel_in.auth
    if auth is None:
        return None
    stored_auth = {"type": auth.type, "value": auth.value.get_secret_value()}
    if isinstance(auth, HeaderWebhookAuth):
        stored_auth["name"] = auth.name
    return stored_auth


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

    async def list_channels(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> Sequence[NotificationChannel]:
        """List all notification channels for a project."""
        # Known gap: project ownership is not verified against the Control Plane;
        # data is isolated by workspace_id only.
        return await self.repository.list_by_project(workspace_id, project_id)

    async def create_channel(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        channel_in: NotificationChannelCreate,
        creator_id: uuid.UUID | None = None,
        background_tasks: BackgroundTasks | None = None,
        email_sender: EmailSender | None = None,
    ) -> NotificationChannel:
        """Create a new notification channel for a project."""
        # Known gap: project ownership is not verified against the Control Plane;
        # data is isolated by workspace_id only.
        channel_id = uuid7()
        channel = NotificationChannel(
            id=channel_id,
            workspace_id=workspace_id,
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


    async def update_channel(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        channel_id: uuid.UUID,
        channel_in: NotificationChannelCreate | WebhookChannelCreate,
    ) -> NotificationChannel:
        channel = await self.repository.get_by_project(
            workspace_id, project_id, channel_id, for_update=True
        )
        if channel is None:
            raise HTTPException(status_code=404, detail="Notification channel not found")
        if channel.channel_type != channel_in.channel_type:
            raise HTTPException(status_code=422, detail="Channel type cannot be changed")

        destination = str(channel_in.destination)
        if isinstance(channel_in, WebhookChannelCreate):
            if "auth" in channel_in.model_fields_set:
                key = settings.webhook_encryption_key
                if key is None or not channel.credentials_encrypted:
                    raise HTTPException(status_code=503, detail="Webhook credentials are unavailable")
                try:
                    cipher = Fernet(key.get_secret_value())
                    credentials = json.loads(cipher.decrypt(channel.credentials_encrypted.encode()))
                    credentials["auth"] = _serialize_webhook_auth(channel_in)
                    channel.credentials_encrypted = cipher.encrypt(
                        json.dumps(credentials).encode()
                    ).decode("ascii")
                except (ValueError, InvalidToken, TypeError):
                    raise HTTPException(status_code=503, detail="Webhook credentials are unavailable") from None
            elif destination != channel.destination:
                raise HTTPException(
                    status_code=422,
                    detail="Choose an authentication option when changing the webhook URL",
                )

        channel.name = channel_in.name
        channel.destination = destination
        if "enabled" in channel_in.model_fields_set:
            channel.enabled = channel_in.enabled
        await self.session.commit()
        return channel

    async def delete_channel(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID, channel_id: uuid.UUID
    ) -> None:
        if not await self.repository.delete_by_project(workspace_id, project_id, channel_id):
            raise HTTPException(status_code=404, detail="Notification channel not found")
        await self.session.commit()

    async def test_channel(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        channel_id: uuid.UUID,
        email_sender: EmailSender,
    ) -> None:
        channel = await self.repository.get_by_project(workspace_id, project_id, channel_id)
        if channel is None:
            raise HTTPException(status_code=404, detail="Notification channel not found")
        if channel.channel_type not in {"email", "webhook"}:
            raise HTTPException(status_code=409, detail="Channel type does not support test delivery")

        # Release the read transaction before waiting for delivery.
        await self.session.commit()
        message = "This is a test notification from Faultline."
        try:
            if channel.channel_type == "webhook":
                await WebhookChannelSender().send_payload(
                    channel,
                    {
                        "event_type": "notification.test",
                        "project_id": str(project_id),
                        "channel_id": str(channel_id),
                        "message": message,
                    },
                    str(uuid7()),
                )
            else:
                await email_sender.send(
                    to_email=channel.destination,
                    subject="[Faultline] Test notification",
                    text_body=message,
                    html_body=f"<p>{message}</p>",
                )
        except WebhookDeliveryError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from None
        except EmailDeliveryError:
            raise HTTPException(status_code=502, detail="Could not send test email") from None

    async def create_webhook_channel(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        channel_in: WebhookChannelCreate,
        authorization: str,
    ) -> WebhookChannelCreated:
        await self._verify_project_access(project_id, authorization)

        key = settings.webhook_encryption_key
        if key is None:
            raise HTTPException(status_code=503, detail="Webhook creation is unavailable")
        try:
            cipher = Fernet(key.get_secret_value())
        except ValueError:
            logger.error("Invalid webhook encryption key configuration")
            raise HTTPException(status_code=503, detail="Webhook creation is unavailable") from None

        signing_secret = "whsec_" + secrets.token_urlsafe(32)
        credentials = json.dumps({
            "signing_secret": signing_secret,
            "auth": _serialize_webhook_auth(channel_in),
        })
        channel = await self.repository.create(NotificationChannel(
            id=uuid7(),
            workspace_id=workspace_id,
            project_id=project_id,
            name=channel_in.name,
            channel_type=channel_in.channel_type,
            destination=str(channel_in.destination),
            enabled=channel_in.enabled,
            credentials_encrypted=cipher.encrypt(credentials.encode()).decode("ascii"),
        ))
        response = WebhookChannelCreated(
            id=channel.id,
            name=channel.name,
            channel_type="webhook",
            destination=channel.destination,
            enabled=channel.enabled,
            created_at=channel.created_at,
            signing_secret=signing_secret,
        )
        await self.session.commit()
        return response

    async def _verify_project_access(self, project_id: uuid.UUID, authorization: str) -> None:
        base_url = settings.control_plane_url
        if base_url is None:
            raise HTTPException(status_code=503, detail="Project verification is unavailable")
        url = f"{str(base_url).rstrip('/')}/api/v1/projects/{project_id}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers={"Authorization": authorization})
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Project verification is unavailable") from None
        if response.status_code in (401, 403, 404):
            raise HTTPException(status_code=404, detail="Project not found")
        if response.status_code != 200:
            raise HTTPException(status_code=503, detail="Project verification is unavailable")
