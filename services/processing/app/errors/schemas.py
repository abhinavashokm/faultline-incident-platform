from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T", bound=Any)

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
