from uuid import UUID

from fastapi import APIRouter, Depends, status
from faultline_auth import Principal, get_principal

from app.delivery.schemas import (
    DeliveryResponse,
    NotificationChannelCreate,
    NotificationChannelResponse,
)

router = APIRouter(tags=["notifications"])


@router.get(
    "/projects/{project_id}/notification-channels",
    response_model=list[NotificationChannelResponse],
    summary="List notification channels",
)
async def list_notification_channels(
    project_id: UUID,
    principal: Principal = Depends(get_principal),
) -> list[NotificationChannelResponse]:
    """List notification channels for a project."""
    return []


@router.post(
    "/projects/{project_id}/notification-channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification channel",
)
async def create_notification_channel(
    project_id: UUID,
    channel_in: NotificationChannelCreate,
    principal: Principal = Depends(get_principal),
) -> NotificationChannelResponse:
    """Create a new notification channel."""
    raise NotImplementedError("Channel creation will be wired in the service implementation")


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
