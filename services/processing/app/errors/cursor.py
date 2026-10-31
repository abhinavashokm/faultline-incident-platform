import base64
from datetime import datetime, timezone
import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status


def _pad_base64(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def encode_issue_cursor(last_seen_at: datetime, issue_id: UUID) -> str:
    """Encode issue cursor as opaque URL-safe base64 string."""
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    data = {
        "last_seen_at": last_seen_at.isoformat(),
        "id": str(issue_id),
    }
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_issue_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode and validate issue cursor. Raises 422 'Invalid cursor' on error."""
    try:
        padded = _pad_base64(cursor)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Cursor must decode to a JSON object")
        if "last_seen_at" not in data or "id" not in data:
            raise ValueError("Missing cursor fields")
        last_seen_at = datetime.fromisoformat(data["last_seen_at"])
        if last_seen_at.tzinfo is None:
            last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
        issue_id = UUID(str(data["id"]))
        return last_seen_at, issue_id
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid cursor",
        ) from exc


def encode_event_cursor(occurred_at: datetime, event_id: UUID) -> str:
    """Encode event cursor as opaque URL-safe base64 string."""
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    data = {
        "occurred_at": occurred_at.isoformat(),
        "id": str(event_id),
    }
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_event_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode and validate event cursor. Raises 422 'Invalid cursor' on error."""
    try:
        padded = _pad_base64(cursor)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Cursor must decode to a JSON object")
        if "occurred_at" not in data or "id" not in data:
            raise ValueError("Missing cursor fields")
        occurred_at = datetime.fromisoformat(data["occurred_at"])
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        event_id = UUID(str(data["id"]))
        return occurred_at, event_id
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid cursor",
        ) from exc
