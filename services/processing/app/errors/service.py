import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors.fingerprint import FINGERPRINT_VERSION, make_fingerprint
from app.errors.repository import ErrorsRepository
from app.errors.schemas import ErrorEventPayload


class ErrorsService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def process_event(self, event: ErrorEventPayload) -> str:
        async with self.session_factory() as session:
            async with session.begin():
                repo = ErrorsRepository(session)

                fingerprint, culprit = make_fingerprint(
                    event.exception_type, event.message, event.stack_frames
                )
                message = (event.message or "")[:2000]
                title = f"{event.exception_type}: {message}"[:500]
                stack_frames: list[dict[str, Any]] = [
                    f.model_dump() if hasattr(f, "model_dump") else f
                    for f in event.stack_frames
                ]

                issue_values = {
                    "id": uuid.uuid4(),
                    "workspace_id": event.workspace_id,
                    "project_id": event.project_id,
                    "fingerprint": fingerprint,
                    "fingerprint_version": FINGERPRINT_VERSION,
                    "title": title,
                    "exception_type": event.exception_type,
                    "culprit": culprit,
                    "level": event.level,
                    "first_seen_at": event.occurred_at,
                    "last_seen_at": event.occurred_at,
                    "first_release": event.release,
                    "last_release": event.release,
                }
                issue_id = await repo.upsert_issue(issue_values)

                event_values = {
                    "id": event.event_id,
                    "workspace_id": event.workspace_id,
                    "project_id": event.project_id,
                    "issue_id": issue_id,
                    "fingerprint": fingerprint,
                    "event_type": event.event_type,
                    "level": event.level,
                    "exception_type": event.exception_type,
                    "message": message,
                    "stack_frames": stack_frames,
                    "service": event.service,
                    "route_template": event.route_template,
                    "http_method": event.http_method,
                    "status_code": event.status_code,
                    "environment": event.environment,
                    "release": event.release,
                    "user_hash": event.user_hash,
                    "context": event.context,
                    "occurred_at": event.occurred_at,
                }
                inserted = await repo.insert_event(event_values)
                if not inserted:
                    return "duplicate, skipped"

                await repo.bump_issue_counters(issue_id, event.occurred_at, event.release)
                return f"saved, issue {issue_id}"

