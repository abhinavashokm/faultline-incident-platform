import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from faultline_auth import Principal, get_principal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.delivery.email import EmailSender, get_email_sender
from app.delivery.schemas import (
    DeliveryResponse,
    NotificationChannelCreate,
    NotificationChannelResponse,
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
    channels = await service.list_channels(project_id)
    return [NotificationChannelResponse.model_validate(c) for c in channels]


@router.post(
    "/projects/{project_id}/notification-channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification channel",
)
async def create_notification_channel(
    project_id: UUID,
    channel_in: NotificationChannelCreate,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
    email_sender: EmailSender = Depends(get_email_sender),
) -> NotificationChannelResponse:
    """Create a new notification channel for a project."""
    service = NotificationChannelService(session)
    channel = await service.create_channel(
        project_id=project_id,
        channel_in=channel_in,
        creator_id=principal.user_id,
        background_tasks=background_tasks,
        email_sender=email_sender,
    )
    return NotificationChannelResponse.model_validate(channel)


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
