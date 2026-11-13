from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationChannelBase(BaseModel):
    name: str = Field(..., max_length=150)
    channel_type: str = Field(..., max_length=30)
    destination: str
    secret_reference: str | None = Field(default=None, max_length=255)
    enabled: bool = True


class NotificationChannelCreate(NotificationChannelBase):
    credentials: str | None = None


class NotificationChannelResponse(NotificationChannelBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime | None = None


class DeliveryAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    delivery_id: UUID
    attempt_number: int
    status: str
    http_status_code: int | None = None
    response_summary: str | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    alert_id: UUID
    channel_id: UUID
    idempotency_key: str
    status: str
    attempt_count: int
    next_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    last_error: str | None = None
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None = None
    attempts: list[DeliveryAttemptResponse] = []
