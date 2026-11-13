import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Standard RFC 5322 simplified email validation pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class NotificationChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    channel_type: Literal["email"] = Field(..., description="Only email channel type is supported")
    destination: str = Field(..., description="Recipient email address")
    enabled: bool = Field(default=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Name cannot be empty or whitespace only")
        if len(trimmed) > 150:
            raise ValueError("Name must be at most 150 characters")
        return trimmed

    @field_validator("destination")
    @classmethod
    def validate_destination_email(cls, v: str) -> str:
        trimmed = v.strip()
        if not EMAIL_REGEX.match(trimmed):
            raise ValueError("Invalid email address format")
        return trimmed


class NotificationChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    channel_type: str
    destination: str
    enabled: bool
    created_at: datetime


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
