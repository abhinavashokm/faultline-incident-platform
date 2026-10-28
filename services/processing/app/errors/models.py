import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

SCHEMA = "processing"


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("project_id", "fingerprint", name="issues_project_fingerprint_uq"),
        UniqueConstraint("project_id", "id", name="issues_project_id_uq"),
        Index("issues_project_status_last_seen_idx", "project_id", "status", "last_seen_at"),
        Index("issues_project_first_seen_idx", "project_id", "first_seen_at"),
        CheckConstraint("level IN ('error', 'warning', 'fatal')", name="issues_level_ck"),
        CheckConstraint(
            "status IN ('unresolved', 'resolved', 'ignored')", name="issues_status_ck"
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))  # opaque, no cross-service FK
    fingerprint: Mapped[str] = mapped_column(CHAR(64))
    fingerprint_version: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    title: Mapped[str] = mapped_column(String(500))
    exception_type: Mapped[str | None] = mapped_column(String(255))
    culprit: Mapped[str | None] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(20), server_default="error")
    status: Mapped[str] = mapped_column(String(20), server_default="unresolved")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occurrence_count: Mapped[int] = mapped_column(BigInteger, server_default="0")
    affected_users_count: Mapped[int] = mapped_column(BigInteger, server_default="0")
    first_release: Mapped[str | None] = mapped_column(String(150))
    last_release: Mapped[str | None] = mapped_column(String(150))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_in_release: Mapped[str | None] = mapped_column(String(150))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ErrorEvent(Base):
    __tablename__ = "error_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "issue_id"],
            [f"{SCHEMA}.issues.project_id", f"{SCHEMA}.issues.id"],
            name="error_events_project_issue_fk",
        ),
        Index("error_events_issue_occurred_idx", "issue_id", "occurred_at"),
        Index("error_events_project_occurred_idx", "project_id", "occurred_at"),
        CheckConstraint("event_type IN ('error', 'message')", name="error_events_type_ck"),
        CheckConstraint("level IN ('error', 'warning', 'fatal')", name="error_events_level_ck"),
        {"schema": SCHEMA},
    )

    # SDK-generated event_id, also the dedup key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    fingerprint: Mapped[str] = mapped_column(CHAR(64))
    event_type: Mapped[str] = mapped_column(String(20), server_default="error")
    level: Mapped[str] = mapped_column(String(20), server_default="error")
    exception_type: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str | None] = mapped_column(String(2000))
    stack_frames: Mapped[list | None] = mapped_column(JSONB)
    service: Mapped[str | None] = mapped_column(String(100))
    route_template: Mapped[str | None] = mapped_column(String(500))
    http_method: Mapped[str | None] = mapped_column(String(10))
    status_code: Mapped[int | None] = mapped_column(SmallInteger)
    environment: Mapped[str | None] = mapped_column(String(100))
    release: Mapped[str | None] = mapped_column(String(150))
    user_hash: Mapped[str | None] = mapped_column(CHAR(64))
    context: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )