from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

T = TypeVar("T", bound=Any)


def _serialize_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# Use shared EventEnvelope if available, or fallback to exact equivalent model
try:
    from faultline_events import EventEnvelope
except ImportError:
    class EventEnvelope(BaseModel, Generic[T]):  # type: ignore[no-redef]
        """Versioned Kafka event envelope for inter-service event communication."""

        schema_version: int = Field(default=1, description="Event envelope schema version")
        event_id: UUID = Field(..., description="Unique event identifier")
        workspace_id: UUID = Field(..., description="Tenant workspace identifier")
        project_id: UUID = Field(..., description="Project identifier")
        received_at: datetime = Field(..., description="UTC timestamp when the server received the event")
        payload: T = Field(..., description="Normalized event payload")

        model_config = ConfigDict(extra="ignore")


class StackFrame(BaseModel):
    file: str = Field(..., max_length=1000)
    function: str = Field(..., max_length=255)
    line: int | None = Field(default=None, ge=0)
    in_app: bool = Field(default=False)

    model_config = ConfigDict(extra="ignore")


class ErrorEventPayload(BaseModel):
    """Consumer-side equivalent of Ingestion's NormalizedErrorEvent payload."""

    event_id: UUID
    occurred_at: datetime
    exception_type: str = Field(..., max_length=255)
    message: str = Field(default="")
    stack_frames: list[StackFrame] = Field(default_factory=list)
    event_type: Literal["error", "message"] = "error"
    level: Literal["error", "warning", "fatal"] = "error"
    service: str | None = Field(default=None, max_length=100)
    route_template: str | None = Field(default=None, max_length=500)
    http_method: str | None = Field(default=None, max_length=10)
    status_code: int | None = Field(default=None)
    environment: str | None = Field(default=None, max_length=100)
    release: str | None = Field(default=None, max_length=150)
    user_hash: str | None = Field(default=None, max_length=64)
    context: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @field_validator("occurred_at")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


@dataclass(frozen=True)
class ProcessedEventResult:
    event_id: UUID
    project_id: UUID
    issue_id: UUID
    is_new: bool
    inserted: bool


# =========================================================================
# HTTP API Request and Response Models
# =========================================================================


class PaginationMeta(BaseModel):
    limit: int
    has_more: bool
    next_cursor: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta


class IssueListItem(BaseModel):
    id: UUID
    title: str
    status: str
    level: str
    exception_type: str | None = None
    culprit: str | None = None
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    first_release: str | None = None
    last_release: str | None = None
    affected_users_count: int

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    @field_serializer("first_seen", "last_seen")
    def serialize_dates(self, v: datetime) -> str | None:
        return _serialize_utc(v)


class IssueDetail(IssueListItem):
    fingerprint: str
    fingerprint_version: int
    resolved_at: datetime | None = None
    resolved_in_release: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("resolved_at", "created_at", "updated_at")
    def serialize_detail_dates(self, v: datetime | None) -> str | None:
        return _serialize_utc(v)


class EventListItem(BaseModel):
    id: UUID
    issue_id: UUID
    occurred_at: datetime
    received_at: datetime
    level: str
    exception_type: str | None = None
    message: str | None = None
    environment: str | None = None
    release: str | None = None
    event_type: str

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    @field_serializer("occurred_at", "received_at")
    def serialize_event_dates(self, v: datetime) -> str | None:
        return _serialize_utc(v)


class EventDetail(EventListItem):
    fingerprint: str
    stack_frames: list[dict[str, Any]] | None = None
    service: str | None = None
    route_template: str | None = None
    http_method: str | None = None
    status_code: int | None = None
    user_hash: str | None = None
    context: dict[str, Any] | None = None


class UpdateIssueStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["resolved", "ignored", "unresolved"]
    resolved_in_release: str | None = None

    @field_validator("resolved_in_release")
    @classmethod
    def validate_resolved_in_release(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("resolved_in_release cannot be empty")
        if len(v) > 150:
            raise ValueError("resolved_in_release must be at most 150 characters")
        return v

    @model_validator(mode="after")
    def check_release_allowed(self) -> "UpdateIssueStatusRequest":
        if self.resolved_in_release is not None and self.status != "resolved":
            raise ValueError("resolved_in_release is allowed only together with status 'resolved'")
        return self
