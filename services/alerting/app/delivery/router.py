import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request, Response, status
from faultline_auth import Principal, get_principal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.delivery.email import EmailSender, get_email_sender
from app.delivery.schemas import (
    DeliveryResponse,
    NotificationChannelCreate,
    NotificationChannelResponse,
    WebhookChannelCreate,
    WebhookChannelCreated,
)
from app.delivery.service import NotificationChannelService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])


@router.get(
    "/projects/{project_id}/notification-channels",
    response_model=list[NotificationChannelResponse],
    summary="List notification channels",
)
async def list_notification_channels(
    project_id: UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationChannelResponse]:
    """List notification channels for a project ordered by created_at desc."""
    service = NotificationChannelService(session)
    channels = await service.list_channels(principal.workspace_id, project_id)
    return [NotificationChannelResponse.model_validate(c) for c in channels]


@router.post(
    "/projects/{project_id}/notification-channels",
    response_model=WebhookChannelCreated | NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification channel",
)
async def create_notification_channel(
    project_id: UUID,
    channel_in: Annotated[
        NotificationChannelCreate | WebhookChannelCreate, Body(discriminator="channel_type")
    ],
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
    email_sender: EmailSender = Depends(get_email_sender),
) -> NotificationChannelResponse:
    """Create a new notification channel for a project."""
    service = NotificationChannelService(session)
    if isinstance(channel_in, WebhookChannelCreate):
        response.headers["Cache-Control"] = "no-store"
        return await service.create_webhook_channel(
            principal.workspace_id, project_id, channel_in, request.headers.get("Authorization", ""),
        )
    channel = await service.create_channel(
        workspace_id=principal.workspace_id,
        project_id=project_id,
        channel_in=channel_in,
        creator_id=principal.user_id,
        background_tasks=background_tasks,
        email_sender=email_sender,
    )
    return NotificationChannelResponse.model_validate(channel)


@router.post(
    "/projects/{project_id}/notification-channels/{channel_id}/test",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Send a test notification",
    responses={
        404: {"description": "Channel not found"},
        409: {"description": "Channel type does not support test delivery"},
        502: {"description": "Test delivery failed"},
    },
)
async def test_notification_channel(
    project_id: UUID,
    channel_id: UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
    email_sender: EmailSender = Depends(get_email_sender),
) -> Response:
    await NotificationChannelService(session).test_channel(
        principal.workspace_id, project_id, channel_id, email_sender
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/projects/{project_id}/notification-channels/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification channel",
)
async def delete_notification_channel(
    project_id: UUID,
    channel_id: UUID,
    principal: Principal = Depends(get_principal),
) -> None:
    """Delete a notification channel."""
    raise NotImplementedError("Channel deletion will be wired in the service implementation")


@router.get(
    "/projects/{project_id}/notification-deliveries",
    response_model=list[DeliveryResponse],
    summary="List delivery attempts",
)
async def list_deliveries(
    project_id: UUID,
    principal: Principal = Depends(get_principal),
) -> list[DeliveryResponse]:
    """List notification deliveries and history."""
    return []


@router.post(
    "/projects/{project_id}/notification-deliveries/{alert_id}/retry",
    response_model=DeliveryResponse,
    summary="Retry notification delivery",
)
async def retry_delivery(
    project_id: UUID,
    alert_id: UUID,
    principal: Principal = Depends(get_principal),
) -> DeliveryResponse:
    """Retry a failed or pending notification delivery."""
    raise NotImplementedError("Delivery retry will be wired in the service implementation")
