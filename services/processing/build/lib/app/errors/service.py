import json
import logging
import re
import uuid
from typing import Any

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.errors.cursor import (
    decode_event_cursor,
    decode_issue_cursor,
    encode_event_cursor,
    encode_issue_cursor,
)
from app.errors.fingerprint import (
    FINGERPRINT_VERSION,
    compute_fingerprint,
    derive_culprit,
    derive_title,
)
from app.errors.repository import ErrorsRepository
from app.errors.schemas import (
    ErrorEventPayload,
    EventDetail,
    EventEnvelope,
    EventListItem,
    IssueDetail,
    IssueListItem,
    PaginatedResponse,
    PaginationMeta,
    ProcessedEventResult,
    UpdateIssueStatusRequest,
)

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


class ErrorsHttpService:
    """Service layer for HTTP API queries and issue status updates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ErrorsRepository(session)

    async def list_issues(
        self,
        workspace_id: UUID,
        project_id: UUID,
        status_filter: str | None,
        limit: int,
        cursor_str: str | None,
    ) -> PaginatedResponse[IssueListItem]:
        cursor = decode_issue_cursor(cursor_str) if cursor_str else None
        rows = await self.repo.list_issues(
            workspace_id=workspace_id,
            project_id=project_id,
            status=status_filter,
            limit=limit,
            cursor=cursor,
        )

        has_more = len(rows) > limit
        if has_more:
            items_data = rows[:limit]
            last_item = items_data[-1]
            next_cursor = encode_issue_cursor(last_item["last_seen"], last_item["id"])
        else:
            items_data = rows
            next_cursor = None

        items = [IssueListItem.model_validate(r) for r in items_data]
        return PaginatedResponse[IssueListItem](
            items=items,
            meta=PaginationMeta(
                limit=limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        )

    async def get_issue_detail(
        self,
        workspace_id: UUID,
        project_id: UUID,
        issue_id: UUID,
    ) -> IssueDetail:
        issue = await self.repo.get_issue_detail(
            workspace_id=workspace_id,
            project_id=project_id,
            issue_id=issue_id,
        )
        if issue is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested resource was not found",
            )
        return IssueDetail(
            id=issue.id,
            title=issue.title,
            status=issue.status,
            level=issue.level,
            exception_type=issue.exception_type,
            culprit=issue.culprit,
            occurrence_count=issue.occurrence_count,
            first_seen=issue.first_seen_at,
            last_seen=issue.last_seen_at,
            first_release=issue.first_release,
            last_release=issue.last_release,
            affected_users_count=issue.affected_users_count,
            fingerprint=issue.fingerprint,
            fingerprint_version=issue.fingerprint_version,
            resolved_at=issue.resolved_at,
            resolved_in_release=issue.resolved_in_release,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )

    async def list_issue_events(
        self,
        workspace_id: UUID,
        project_id: UUID,
        issue_id: UUID,
        limit: int,
        cursor_str: str | None,
    ) -> PaginatedResponse[EventListItem]:
        issue = await self.repo.get_issue_detail(
            workspace_id=workspace_id,
            project_id=project_id,
            issue_id=issue_id,
        )
        if issue is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested resource was not found",
            )

        cursor = decode_event_cursor(cursor_str) if cursor_str else None
        rows = await self.repo.list_events(
            workspace_id=workspace_id,
            project_id=project_id,
            issue_id=issue_id,
            limit=limit,
            cursor=cursor,
        )

        has_more = len(rows) > limit
        if has_more:
            items_data = rows[:limit]
            last_item = items_data[-1]
            next_cursor = encode_event_cursor(last_item["occurred_at"], last_item["id"])
        else:
            items_data = rows
            next_cursor = None

        items = [EventListItem.model_validate(r) for r in items_data]
        return PaginatedResponse[EventListItem](
            items=items,
            meta=PaginationMeta(
                limit=limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        )

    async def get_event_detail(
        self,
        workspace_id: UUID,
        project_id: UUID,
        issue_id: UUID,
        event_id: UUID,
    ) -> EventDetail:
        event = await self.repo.get_event_detail(
            workspace_id=workspace_id,
            project_id=project_id,
            issue_id=issue_id,
            event_id=event_id,
        )
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested resource was not found",
            )
        return EventDetail(
            id=event.id,
            issue_id=event.issue_id,
            occurred_at=event.occurred_at,
            received_at=event.received_at,
            level=event.level,
            exception_type=event.exception_type,
            message=event.message,
            environment=event.environment,
            release=event.release,
            event_type=event.event_type,
            fingerprint=event.fingerprint,
            stack_frames=event.stack_frames,
            service=event.service,
            route_template=event.route_template,
            http_method=event.http_method,
            status_code=event.status_code,
            user_hash=event.user_hash,
            context=event.context,
        )

    async def update_issue_status(
        self,
        workspace_id: UUID,
        project_id: UUID,
        issue_id: UUID,
        body: UpdateIssueStatusRequest,
        user_id: UUID,
    ) -> IssueDetail:
        issue = await self.repo.update_issue_status(
            workspace_id=workspace_id,
            project_id=project_id,
            issue_id=issue_id,
            new_status=body.status,
            resolved_in_release=body.resolved_in_release,
            user_id=user_id,
        )
        if issue is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested resource was not found",
            )

        await self.session.commit()
        logger.info(
            "Issue status updated: issue_id=%s status=%s user_id=%s",
            issue_id,
            body.status,
            user_id,
        )

        return IssueDetail(
            id=issue.id,
            title=issue.title,
            status=issue.status,
            level=issue.level,
            exception_type=issue.exception_type,
            culprit=issue.culprit,
            occurrence_count=issue.occurrence_count,
            first_seen=issue.first_seen_at,
            last_seen=issue.last_seen_at,
            first_release=issue.first_release,
            last_release=issue.last_release,
            affected_users_count=issue.affected_users_count,
            fingerprint=issue.fingerprint,
            fingerprint_version=issue.fingerprint_version,
            resolved_at=issue.resolved_at,
            resolved_in_release=issue.resolved_in_release,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )
