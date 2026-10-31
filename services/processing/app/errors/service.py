import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.errors.fingerprint import (
    FINGERPRINT_VERSION,
    compute_fingerprint,
    derive_culprit,
    derive_title,
)
from app.errors.repository import ErrorsRepository
from app.errors.schemas import ErrorEventPayload, EventEnvelope, ProcessedEventResult

logger = logging.getLogger(__name__)

# Control characters pattern (exclude \t, \n, \r)
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def normalize_level(level: str | None) -> str:
    """Map level to schema CHECK values ('error', 'warning', 'fatal'). Unknown -> 'error'."""
    raw = (level or "").strip().lower()
    if raw in ("error", "warning", "fatal"):
        return raw
    if raw in ("warn",):
        return "warning"
    if raw in ("critical", "fatal", "panic"):
        return "fatal"
    return "error"


def normalize_event_type(event_type: str | None) -> str:
    """Limit event_type to 'error' or 'message'. Unknown -> 'error'."""
    raw = (event_type or "").strip().lower()
    return raw if raw in ("error", "message") else "error"


def scrub_message(msg: str | None) -> str:
    """Scrub control characters and truncate to 2000 characters."""
    raw = msg or ""
    scrubbed = CONTROL_CHAR_PATTERN.sub("", raw)
    return scrubbed[:2000]


def cap_context(context: dict[str, Any] | None, max_bytes: int) -> dict[str, Any]:
    """Ensure context serialized size is within max_bytes. Truncate to marker if exceeded."""
    ctx = context or {}
    try:
        serialized = json.dumps(ctx).encode("utf-8")
        if len(serialized) > max_bytes:
            return {"_truncated": True}
        return ctx
    except Exception:
        return {"_truncated": True}


class ErrorsService:
    """Owns business rules, normalization, fingerprinting, and database transaction boundaries.

    Does not know about Kafka.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def process_event(
        self,
        envelope: EventEnvelope[ErrorEventPayload],
    ) -> ProcessedEventResult:
        payload = envelope.payload

        # 1. Normalization
        message = scrub_message(payload.message)
        title = derive_title(payload.exception_type, message)
        culprit = derive_culprit(payload.stack_frames, payload.route_template)
        level = normalize_level(payload.level)
        event_type = normalize_event_type(payload.event_type)
        environment = payload.environment.lower() if payload.environment else None
        context = cap_context(payload.context, settings.context_byte_cap)

        status_code = payload.status_code
        if status_code is not None and not (-32768 <= status_code <= 32767):
            status_code = None

        stack_frames_data = [
            {
                "file": str(f.file),
                "function": str(f.function),
                "line": f.line,
                "in_app": bool(f.in_app),
            }
            for f in payload.stack_frames
        ]

        # 2. Fingerprinting
        fingerprint = compute_fingerprint(
            exception_type=payload.exception_type,
            stack_frames=payload.stack_frames,
            route_template=payload.route_template,
            message=message,
        )

        # 3. Transaction boundary (one transaction per message)
        async with self.session_factory() as session:
            async with session.begin():
                repo = ErrorsRepository(session)

                # Step 1: Upsert issue
                issue_values: dict[str, Any] = {
                    "id": uuid.uuid4(),
                    "workspace_id": envelope.workspace_id,
                    "project_id": envelope.project_id,
                    "fingerprint": fingerprint,
                    "fingerprint_version": FINGERPRINT_VERSION,
                    "title": title,
                    "exception_type": payload.exception_type[:255] if payload.exception_type else None,
                    "culprit": culprit,
                    "level": level,
                    "status": "unresolved",
                    "first_seen_at": payload.occurred_at,
                    "last_seen_at": payload.occurred_at,
                    "occurrence_count": 0,
                    "affected_users_count": 0,
                    "first_release": payload.release[:150] if payload.release else None,
                    "last_release": payload.release[:150] if payload.release else None,
                }
                issue_id, is_new = await repo.upsert_issue(issue_values)

                # Step 2: Insert error event
                event_values: dict[str, Any] = {
                    "id": envelope.event_id,
                    "workspace_id": envelope.workspace_id,
                    "project_id": envelope.project_id,
                    "issue_id": issue_id,
                    "fingerprint": fingerprint,
                    "event_type": event_type,
                    "level": level,
                    "exception_type": payload.exception_type[:255] if payload.exception_type else None,
                    "message": message,
                    "stack_frames": stack_frames_data,
                    "service": payload.service[:100] if payload.service else None,
                    "route_template": payload.route_template[:500] if payload.route_template else None,
                    "http_method": payload.http_method[:10] if payload.http_method else None,
                    "status_code": status_code,
                    "environment": environment[:100] if environment else None,
                    "release": payload.release[:150] if payload.release else None,
                    "user_hash": payload.user_hash[:64] if payload.user_hash else None,
                    "context": context,
                    "occurred_at": payload.occurred_at,
                    "received_at": envelope.received_at,
                }
                inserted = await repo.insert_event(event_values)

                # Step 3: Bump counters only when event was actually inserted
                if inserted:
                    await repo.bump_issue_counters(
                        issue_id=issue_id,
                        occurred_at=payload.occurred_at,
                        release=payload.release[:150] if payload.release else None,
                    )

                return ProcessedEventResult(
                    event_id=envelope.event_id,
                    project_id=envelope.project_id,
                    issue_id=issue_id,
                    is_new=is_new,
                    inserted=inserted,
                )
