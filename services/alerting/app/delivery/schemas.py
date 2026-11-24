import re
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, SecretStr, UrlConstraints, field_validator

# Standard RFC 5322 simplified email validation pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class ChannelCreateFields(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
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


class NotificationChannelCreate(ChannelCreateFields):
    channel_type: Literal["email"]
    destination: str

    @field_validator("destination")
    @classmethod
    def validate_destination_email(cls, v: str) -> str:
        trimmed = v.strip()
        if not EMAIL_REGEX.match(trimmed):
            raise ValueError("Invalid email address format")
        return trimmed


class WebhookAuthValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: SecretStr

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not raw.strip() or not re.fullmatch(r"[ -~]+", raw):
            raise ValueError("Credential must contain printable ASCII characters")
        return value


class BearerWebhookAuth(WebhookAuthValue):
    type: Literal["bearer"]


class HeaderWebhookAuth(WebhookAuthValue):
    type: Literal["header"]
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9-]+", value):
            raise ValueError("Invalid header name")
        reserved = {"host", "content-length", "content-type", "authorization", "connection", "transfer-encoding"}
        if value.lower() in reserved or value.lower().startswith("x-faultline-"):
            raise ValueError("Reserved header name")
        return value


class WebhookChannelCreate(ChannelCreateFields):
    model_config = ConfigDict(extra="forbid")

    channel_type: Literal["webhook"]
    destination: Annotated[AnyUrl, UrlConstraints(allowed_schemes=["https"], host_required=True)]
    auth: Annotated[BearerWebhookAuth | HeaderWebhookAuth, Field(discriminator="type")] | None = None

    @field_validator("destination")
    @classmethod
    def validate_url(cls, value: AnyUrl) -> AnyUrl:
        if value.username is not None or value.password is not None or value.fragment is not None:
            raise ValueError("Webhook URL must not contain user credentials or a fragment")
        return value


class NotificationChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    channel_type: str
    destination: str
    enabled: bool
    created_at: datetime


class WebhookChannelCreated(NotificationChannelResponse):
    channel_type: Literal["webhook"]
    signing_secret: str


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
