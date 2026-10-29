"""create control plane tables

Revision ID: 0001
Revises:
Create Date: 2026-10-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'suspended', 'deleted')", name="users_status_ck"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="users_email_uq"),
        schema="control",
    )

    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="workspaces_slug_ck"),
        sa.CheckConstraint("status IN ('active', 'suspended', 'deleted')", name="workspaces_status_ck"),
        sa.ForeignKeyConstraint(["created_by"], ["control.users.id"], ondelete="RESTRICT", name="workspaces_created_by_fk"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="workspaces_slug_uq"),
        schema="control",
    )

    op.create_table(
        "workspace_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="workspace_members_role_ck"),
        sa.ForeignKeyConstraint(["invited_by"], ["control.users.id"], name="workspace_members_invited_by_fk"),
        sa.ForeignKeyConstraint(["user_id"], ["control.users.id"], name="workspace_members_user_fk"),
        sa.ForeignKeyConstraint(["workspace_id"], ["control.workspaces.id"], ondelete="CASCADE", name="workspace_members_workspace_fk"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="workspace_members_workspace_user_uq"),
        schema="control",
    )
    op.create_index(
        "workspace_members_user_id_idx",
        "workspace_members",
        ["user_id"],
        unique=False,
        schema="control",
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="projects_slug_ck"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="projects_status_ck"),
        sa.ForeignKeyConstraint(["created_by"], ["control.users.id"], ondelete="RESTRICT", name="projects_created_by_fk"),
        sa.ForeignKeyConstraint(["workspace_id"], ["control.workspaces.id"], ondelete="CASCADE", name="projects_workspace_fk"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "id", name="projects_workspace_id_uq"),
        sa.UniqueConstraint("workspace_id", "slug", name="projects_workspace_slug_uq"),
        schema="control",
    )

    op.create_table(
        "project_api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("key_type", sa.String(length=20), nullable=False),
        sa.Column("key_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("public_key", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("key_type IN ('ingest', 'release')", name="project_api_keys_key_type_ck"),
        sa.ForeignKeyConstraint(["created_by"], ["control.users.id"], ondelete="RESTRICT", name="project_api_keys_created_by_fk"),
        sa.ForeignKeyConstraint(["workspace_id", "project_id"], ["control.projects.workspace_id", "control.projects.id"], name="project_api_keys_project_fk"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", name="project_api_keys_key_hash_uq"),
        sa.UniqueConstraint("public_key", name="project_api_keys_public_key_uq"),
        schema="control",
    )
    op.create_index(
        "project_api_keys_project_id_idx",
        "project_api_keys",
        ["project_id"],
        unique=False,
        schema="control",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "project_api_keys_project_id_idx",
        table_name="project_api_keys",
        schema="control",
    )
    op.drop_table("project_api_keys", schema="control")
    op.drop_table("projects", schema="control")
    op.drop_index(
        "workspace_members_user_id_idx",
        table_name="workspace_members",
        schema="control",
    )
    op.drop_table("workspace_members", schema="control")
    op.drop_table("workspaces", schema="control")
    op.drop_table("users", schema="control")
    op.execute("DROP EXTENSION IF EXISTS citext")

