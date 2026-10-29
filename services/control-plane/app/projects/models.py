import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

SCHEMA = "control"


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id"],
            [f"{SCHEMA}.workspaces.id"],
            ondelete="CASCADE",
            name="projects_workspace_fk",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.users.id"],
            ondelete="RESTRICT",
            name="projects_created_by_fk",
        ),
        UniqueConstraint("workspace_id", "slug", name="projects_workspace_slug_uq"),
        UniqueConstraint("workspace_id", "id", name="projects_workspace_id_uq"),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="projects_status_ck",
        ),
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="projects_slug_ck",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class ProjectApiKey(Base):
    __tablename__ = "project_api_keys"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            [f"{SCHEMA}.projects.workspace_id", f"{SCHEMA}.projects.id"],
            name="project_api_keys_project_fk",
        ),
        ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.users.id"],
            ondelete="RESTRICT",
            name="project_api_keys_created_by_fk",
        ),
        UniqueConstraint("key_hash", name="project_api_keys_key_hash_uq"),
        UniqueConstraint("public_key", name="project_api_keys_public_key_uq"),
        Index("project_api_keys_project_id_idx", "project_id"),
        CheckConstraint(
            "key_type IN ('ingest', 'release')",
            name="project_api_keys_key_type_ck",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    key_type: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    public_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

