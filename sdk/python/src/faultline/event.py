from datetime import datetime, timezone
import re
from typing import Any, Literal
import uuid

from faultline._internal import truncate_string
from faultline.stacktrace import extract_stack_frames

ENV_PATTERN = re.compile(r"^[a-z0-9_-]+$")


def normalize_environment(env: str | None) -> str | None:
    """Normalize and validate environment name."""
    if not env:
        return None
    cleaned = env.strip().lower()[:100]
    # Replace non-conforming characters with hyphen to ensure ^[a-z0-9_-]+$
    cleaned = re.sub(r"[^a-z0-9_-]", "-", cleaned)
    return cleaned if cleaned else None


def normalize_http_method(method: str | None) -> str | None:
    """Normalize HTTP method string."""
    if not method:
        return None
    return method.strip().upper()[:10]


def build_error_event(
    exc: BaseException,
    *,
    release: str | None = None,
    environment: str | None = None,
    service: str | None = None,
    route_template: str | None = None,
    http_method: str | None = None,
    status_code: int | None = None,
    user_hash: str | None = None,
    context: dict[str, Any] | None = None,
    level: Literal["error", "warning", "fatal"] = "error",
) -> dict[str, Any]:
    """Build a structured error event dict matching the Faultline ingestion schema."""
    event_id = str(uuid.uuid4())
    occurred_at = datetime.now(timezone.utc).isoformat()
    exception_type = truncate_string(type(exc).__name__, 255) or "Exception"
    message = truncate_string(str(exc), 2000)
    stack_frames = extract_stack_frames(exc)

    return {
        "event_id": event_id,
        "occurred_at": occurred_at,
        "exception_type": exception_type,
        "message": message,
        "stack_frames": stack_frames,
        "event_type": "error",
        "level": level if level in ("error", "warning", "fatal") else "error",
        "service": truncate_string(service, 100) or None,
        "route_template": truncate_string(route_template, 500) or None,
        "http_method": normalize_http_method(http_method),
        "status_code": status_code,
        "environment": normalize_environment(environment),
        "release": truncate_string(release, 150) or None,
        "user_hash": truncate_string(user_hash, 64) or None,
        "context": context if isinstance(context, dict) else {},
    }


def build_message_event(
    message: str,
    *,
    level: Literal["error", "warning", "fatal"] = "warning",
    release: str | None = None,
    environment: str | None = None,
    service: str | None = None,
    route_template: str | None = None,
    http_method: str | None = None,
    status_code: int | None = None,
    user_hash: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a custom message event dict matching the Faultline ingestion schema."""
    event_id = str(uuid.uuid4())
    occurred_at = datetime.now(timezone.utc).isoformat()
    msg_str = truncate_string(message, 2000)

    return {
        "event_id": event_id,
        "occurred_at": occurred_at,
        "exception_type": "Message",
        "message": msg_str,
        "stack_frames": extract_stack_frames(None),
        "event_type": "message",
        "level": level if level in ("error", "warning", "fatal") else "warning",
        "service": truncate_string(service, 100) or None,
        "route_template": truncate_string(route_template, 500) or None,
        "http_method": normalize_http_method(http_method),
        "status_code": status_code,
        "environment": normalize_environment(environment),
        "release": truncate_string(release, 150) or None,
        "user_hash": truncate_string(user_hash, 64) or None,
        "context": context if isinstance(context, dict) else {},
    }

