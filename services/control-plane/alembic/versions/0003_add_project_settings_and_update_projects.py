"""add project settings and update projects and api keys

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Update control.projects
    op.add_column(
        "projects",
        sa.Column("archived_by", sa.UUID(), nullable=True),
        schema="control",
    )
    op.create_foreign_key(
        "projects_archived_by_fk",
        "projects",
        "users",
        ["archived_by"],
        ["id"],
        source_schema="control",
        referent_schema="control",
    )
    op.create_check_constraint(
        "projects_archived_consistency_ck",
        "projects",
        "(status = 'archived' AND archived_at IS NOT NULL AND archived_by IS NOT NULL) "
        "OR (status = 'active' AND archived_at IS NULL AND archived_by IS NULL)",
        schema="control",
    )

    # 2. Update control.project_api_keys
    op.alter_column(
        "project_api_keys",
        "key_hash",
        existing_type=sa.CHAR(length=64),
        nullable=True,
        schema="control",
    )
    op.alter_column(
        "project_api_keys",
        "key_prefix",
        existing_type=sa.String(length=16),
        nullable=True,
        schema="control",
    )
    op.create_check_constraint(
        "project_api_keys_key_type_consistency_ck",
        "project_api_keys",
        "(key_type = 'ingest' AND public_key IS NOT NULL AND key_hash IS NULL AND key_prefix IS NULL) "
        "OR (key_type = 'release' AND key_hash IS NOT NULL AND key_prefix IS NOT NULL AND public_key IS NULL)",
        schema="control",
    )

    # 3. Create control.project_settings
    op.create_table(
        "project_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("retention_days", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("ignored_status_codes", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("retention_days > 0", name="project_settings_retention_days_ck"),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["control.projects.workspace_id", "control.projects.id"],
            ondelete="CASCADE",
            name="project_settings_project_fk",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["control.users.id"],
            name="project_settings_updated_by_fk",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="project_settings_project_id_uq"),
        sa.UniqueConstraint("workspace_id", "project_id", name="project_settings_workspace_project_uq"),
        schema="control",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("project_settings", schema="control")
    op.drop_constraint(
        "project_api_keys_key_type_consistency_ck",
        "project_api_keys",
        schema="control",
        type_="check",
    )
    op.alter_column(
        "project_api_keys",
        "key_prefix",
        existing_type=sa.String(length=16),
        nullable=False,
        schema="control",
    )
    op.alter_column(
        "project_api_keys",
        "key_hash",
        existing_type=sa.CHAR(length=64),
        nullable=False,
        schema="control",
    )
    op.drop_constraint(
        "projects_archived_consistency_ck",
        "projects",
        schema="control",
        type_="check",
    )
    op.drop_constraint(
        "projects_archived_by_fk",
        "projects",
        schema="control",
        type_="foreignkey",
    )
    op.drop_column("projects", "archived_by", schema="control")

