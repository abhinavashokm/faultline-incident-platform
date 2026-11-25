from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_workspace_project_created_at", "workspace_id", "project_id", "created_at"),
        {"schema": "incidents"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID]
    project_id: Mapped[UUID]
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(30), server_default="medium")
    status: Mapped[str] = mapped_column(String(30), server_default="open")
    created_by: Mapped[UUID]
    assigned_to: Mapped[UUID | None]
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IncidentIssue(Base):
    __tablename__ = "incident_issues"
    __table_args__ = (UniqueConstraint("incident_id", "issue_id"), {"schema": "incidents"})

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incidents.id"))
    issue_id: Mapped[UUID]
    issue_title: Mapped[str | None] = mapped_column(String(255))
    error_type: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime | None]
    last_seen_at: Mapped[datetime | None]
    occurrence_count: Mapped[int | None] = mapped_column(BigInteger)
    snapshot_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IncidentTimelineEntry(Base):
    __tablename__ = "incident_timeline"
    __table_args__ = (
        Index("ix_incident_timeline_incident_created_at", "incident_id", "created_at"),
        {"schema": "incidents"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.incidents.id"))
    actor_id: Mapped[UUID | None]
    event_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    event_metadata: Mapped[dict[str, object] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
