import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
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
        ForeignKeyConstraint(
            ["archived_by"],
            [f"{SCHEMA}.users.id"],
            name="projects_archived_by_fk",
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
        CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL AND archived_by IS NOT NULL) "
            "OR (status = 'active' AND archived_at IS NULL AND archived_by IS NULL)",
            name="projects_archived_consistency_ck",
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
    archived_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
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
        CheckConstraint(
            "(key_type = 'ingest' AND public_key IS NOT NULL AND key_hash IS NULL AND key_prefix IS NULL) "
            "OR (key_type = 'release' AND key_hash IS NOT NULL AND key_prefix IS NOT NULL AND public_key IS NULL)",
            name="project_api_keys_key_type_consistency_ck",
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
    key_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    key_prefix: Mapped[str | None] = mapped_column(String(16), nullable=True)
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


class ProjectSettings(Base):
    __tablename__ = "project_settings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            [f"{SCHEMA}.projects.workspace_id", f"{SCHEMA}.projects.id"],
            ondelete="CASCADE",
            name="project_settings_project_fk",
        ),
        ForeignKeyConstraint(
            ["updated_by"],
            [f"{SCHEMA}.users.id"],
            name="project_settings_updated_by_fk",
        ),
        UniqueConstraint("workspace_id", "project_id", name="project_settings_workspace_project_uq"),
        UniqueConstraint("project_id", name="project_settings_project_id_uq"),
        CheckConstraint("retention_days > 0", name="project_settings_retention_days_ck"),
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
    retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default=text("30")
    )
    ignored_status_codes: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer), nullable=True
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            [f"{SCHEMA}.projects.workspace_id", f"{SCHEMA}.projects.id"],
            name="releases_project_fk",
        ),
        ForeignKeyConstraint(
            ["created_by_key_id"],
            [f"{SCHEMA}.project_api_keys.id"],
            name="releases_created_by_key_fk",
        ),
        UniqueConstraint("project_id", "version", name="releases_project_version_uq"),
        UniqueConstraint("workspace_id", "project_id", "id", name="releases_workspace_project_id_uq"),
        Index("releases_project_created_at_idx", "project_id", "created_at"),
        Index("releases_project_commit_sha_idx", "project_id", "commit_sha"),
        CheckConstraint("version <> '' AND version !~ '[[:space:]]'", name="releases_version_ck"),
        CheckConstraint("commit_sha ~ '^[0-9a-f]+$'", name="releases_commit_sha_ck"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    version: Mapped[str] = mapped_column(String(150))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    artifact_ref: Mapped[str | None] = mapped_column(String(300))
    created_by_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Deployment(Base):
    __tablename__ = "deployments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            [f"{SCHEMA}.projects.workspace_id", f"{SCHEMA}.projects.id"],
            name="deployments_project_fk",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "release_id"],
            [f"{SCHEMA}.releases.workspace_id", f"{SCHEMA}.releases.project_id", f"{SCHEMA}.releases.id"],
            name="deployments_release_fk",
        ),
        ForeignKeyConstraint(
            ["rollback_of_deployment_id"],
            [f"{SCHEMA}.deployments.id"],
            name="deployments_rollback_of_fk",
        ),
        ForeignKeyConstraint(
            ["deployed_by"],
            [f"{SCHEMA}.users.id"],
            name="deployments_deployed_by_fk",
        ),
        ForeignKeyConstraint(
            ["deployed_by_key_id"],
            [f"{SCHEMA}.project_api_keys.id"],
            name="deployments_deployed_by_key_fk",
        ),
        Index("deployments_project_environment_created_at_idx", "project_id", "environment", "created_at"),
        UniqueConstraint("project_id", "external_run_id", name="deployments_project_external_run_uq"),
        Index(
            "deployments_project_environment_active_uq",
            "project_id",
            "environment",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
        CheckConstraint("environment ~ '^[a-z0-9_-]+$'", name="deployments_environment_ck"),
        CheckConstraint("kind IN ('deploy', 'rollback')", name="deployments_kind_ck"),
        CheckConstraint(
            "status IN ('pending', 'running', 'success', 'failed', 'cancelled', 'rolled_back')",
            name="deployments_status_ck",
        ),
        CheckConstraint(
            "(deployed_by IS NULL) <> (deployed_by_key_id IS NULL)",
            name="deployments_actor_ck",
        ),
        CheckConstraint("finished_at >= started_at", name="deployments_finished_at_ck"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    environment: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20), server_default="deploy")
    status: Mapped[str] = mapped_column(String(30), server_default="pending")
    rollback_of_deployment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    external_run_id: Mapped[str | None] = mapped_column(String(100))
    deployed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    deployed_by_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    deployment_metadata: Mapped[dict[str, object] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
