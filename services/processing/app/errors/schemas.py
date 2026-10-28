from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StackFrame(BaseModel):
    file: str
    function: str
    line: int | None = None
    in_app: bool = False


class ErrorEventPayload(BaseModel):
    event_id: UUID
    workspace_id: UUID
    project_id: UUID
    occurred_at: datetime
    exception_type: str
    message: str = ""
    stack_frames: list[StackFrame] = Field(default_factory=list)
    event_type: Literal["error", "message"] = "error"
    level: Literal["error", "warning", "fatal"] = "error"
    service: str | None = None
    route_template: str | None = None
    http_method: str | None = None
    status_code: int | None = None
    environment: str | None = None
    release: str | None = None
    user_hash: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

