"""Create the schema and tables used by incident creation."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CreateSchema, DropSchema

revision: str = "0001_initial_incident"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

SCHEMA = "incidents"


def upgrade() -> None:
    op.execute(CreateSchema(SCHEMA, if_not_exists=True))
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("severity", sa.String(30), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("assigned_to", sa.Uuid()),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("closed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_incidents_workspace_project_created_at",
        "incidents",
        ["workspace_id", "project_id", "created_at"],
        schema=SCHEMA,
    )
    op.create_table(
        "incident_issues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "incident_id", sa.Uuid(), sa.ForeignKey("incidents.incidents.id"), nullable=False
        ),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("issue_title", sa.String(255)),
        sa.Column("error_type", sa.String(255)),
        sa.Column("error_message", sa.Text()),
        sa.Column("first_seen_at", sa.DateTime()),
        sa.Column("last_seen_at", sa.DateTime()),
        sa.Column("occurrence_count", sa.BigInteger()),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("incident_id", "issue_id"),
        schema=SCHEMA,
    )
    op.create_table(
        "incident_timeline",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "incident_id", sa.Uuid(), sa.ForeignKey("incidents.incidents.id"), nullable=False
        ),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_incident_timeline_incident_created_at",
        "incident_timeline",
        ["incident_id", "created_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("incident_timeline", schema=SCHEMA)
    op.drop_table("incident_issues", schema=SCHEMA)
    op.drop_table("incidents", schema=SCHEMA)
    op.execute(DropSchema(SCHEMA))
