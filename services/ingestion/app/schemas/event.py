import json
import re
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import settings

# Sensitive keys pattern: case-insensitive check
SENSITIVE_KEY_PATTERN = re.compile(
    r"(auth|cookie|password|passwd|token|secret|api[_-]?key|card|cvv|ssn)",
    re.IGNORECASE,
)

# Credit card number pattern (13 to 19 digits with optional spaces or dashes)
CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

# Environment format: lowercase alphanumeric, hyphens, and underscores
ENV_PATTERN = re.compile(r"^[a-z0-9_-]+$")


def redact_sensitive_data(obj: Any, key_name: str | None = None) -> Any:
    """Recursively scrub sensitive keys and credit card numbers from a dictionary/list."""
    if key_name and SENSITIVE_KEY_PATTERN.search(key_name):
        return "[REDACTED]"

    if isinstance(obj, dict):
        return {
            k: redact_sensitive_data(v, key_name=str(k))
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [redact_sensitive_data(item, key_name=key_name) for item in obj]
    elif isinstance(obj, str):
        if CARD_NUMBER_PATTERN.search(obj):
            return CARD_NUMBER_PATTERN.sub("[REDACTED]", obj)
        return obj
    return obj


class StackFrame(BaseModel):
    file: str = Field(..., max_length=1000)
    function: str = Field(..., max_length=255)
    line: int | None = Field(default=None, ge=0)
    in_app: bool = Field(default=False)

    model_config = ConfigDict(extra="ignore")


class ErrorEventIngestRequest(BaseModel):
    """Client request schema for error event ingestion.
    Note: workspace_id and project_id are NOT part of this schema; they are server-derived.
    """
    event_id: UUID
    occurred_at: datetime
    exception_type: str = Field(..., max_length=255)
    message: str = Field(default="")
    stack_frames: list[StackFrame] = Field(default_factory=list)
    event_type: Literal["error", "message"] = "error"
    level: Literal["error", "warning", "fatal"] = "error"
    service: str | None = Field(default=None, max_length=100)
    route_template: str | None = Field(default=None, max_length=500)
    http_method: str | None = Field(default=None)
    status_code: int | None = Field(default=None, ge=-32768, le=32767)
    environment: str | None = Field(default=None, max_length=100)
    release: str | None = Field(default=None, max_length=150)
    user_hash: str | None = Field(default=None, max_length=64)
    context: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @field_validator("message")
    @classmethod
    def truncate_message(cls, v: str) -> str:
        """Truncate message to 2000 characters."""
        if len(v) > 2000:
            return v[:2000]
        return v

    @field_validator("http_method")
    @classmethod
    def normalize_http_method(cls, v: str | None) -> str | None:
        """Uppercase and validate http_method length <= 10."""
        if v is None:
            return None
        v = v.strip().upper()
        if len(v) > 10:
            raise ValueError("http_method must be at most 10 characters")
        return v

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, v: str | None) -> str | None:
        """Lowercase and validate environment pattern ^[a-z0-9_-]+$."""
        if v is None:
            return None
        v = v.strip().lower()
        if len(v) > 100:
            raise ValueError("environment must be at most 100 characters")
        if not ENV_PATTERN.match(v):
            raise ValueError("environment must match ^[a-z0-9_-]+$")
        return v

    @field_validator("user_hash")
    @classmethod
    def validate_user_hash(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 64:
            raise ValueError("user_hash must be at most 64 characters")
        return v

    @field_validator("stack_frames")
    @classmethod
    def cap_stack_frames(cls, v: list[StackFrame]) -> list[StackFrame]:
        """Cap stack_frames count to max_stack_frames."""
        if len(v) > settings.max_stack_frames:
            # Preserve the most recent frames (innermost call site)
            return v[-settings.max_stack_frames:]
        return v

    @field_validator("context")
    @classmethod
    def validate_and_redact_context(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Scrub sensitive keys and verify serialized size is within bounds."""
        redacted = redact_sensitive_data(v)
        try:
            serialized = json.dumps(redacted)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"context is not JSON serializable: {exc}") from exc

        if len(serialized.encode("utf-8")) > settings.max_context_bytes:
            raise ValueError(f"context exceeds maximum allowed size of {settings.max_context_bytes} bytes")
        return redacted


class NormalizedErrorEvent(BaseModel):
    """Normalized payload that is packaged inside EventEnvelope for Kafka."""
    event_id: UUID
    occurred_at: datetime
    exception_type: str
    message: str
    stack_frames: list[StackFrame] = Field(default_factory=list)
    event_type: Literal["error", "message"]
    level: Literal["error", "warning", "fatal"]
    service: str | None = None
    route_template: str | None = None
    http_method: str | None = None
    status_code: int | None = None
    environment: str | None = None
    release: str | None = None
    user_hash: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class IngestResponse(BaseModel):
    event_id: UUID
    status: Literal["accepted"] = "accepted"

