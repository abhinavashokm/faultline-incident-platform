"""Scope alerting records to their tenant workspace.

Revision ID: 0003_workspace_isolation
Revises: 0002_processed_events
"""

import json
import os
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_workspace_isolation"
down_revision = "0002_processed_events"
branch_labels = None
depends_on = None

SCHEMA = "alerting"
BACKFILL_ENV = "ALERTING_WORKSPACE_BACKFILL_BY_PROJECT"
TABLES = ("alert_rules", "alert_states", "alerts", "notification_channels", "deliveries")
WORKSPACE_INDEXES = (
    ("ix_alerting_alert_rules_workspace_project", "alert_rules", ["workspace_id", "project_id"]),
    (
        "ix_alerting_alerts_workspace_project_status_last_triggered",
        "alerts",
        ["workspace_id", "project_id", "status", "last_triggered_at"],
    ),
    (
        "ix_alerting_notification_channels_workspace_project",
        "notification_channels",
        ["workspace_id", "project_id"],
    ),
)
OLD_ALERT_INDEX = "ix_alerting_alerts_project_status_last_triggered"


def upgrade() -> None:
    raw_mapping = json.loads(os.environ.get(BACKFILL_ENV, "{}"))
    if not isinstance(raw_mapping, dict):
        raise ValueError(f"{BACKFILL_ENV} must be a JSON object mapping project UUIDs to workspace UUIDs")
    workspace_by_project = {UUID(project): UUID(workspace) for project, workspace in raw_mapping.items()}

    connection = op.get_bind()
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
            schema=SCHEMA,
        )

    for table in TABLES:
        projects = connection.execute(
            sa.text(f"SELECT DISTINCT project_id FROM {SCHEMA}.{table}")
        ).scalars()
        for project in projects:
            if project not in workspace_by_project:
                raise ValueError(f"Missing project {project} from {BACKFILL_ENV} (required by {table})")
            connection.execute(
                sa.text(
                    f"UPDATE {SCHEMA}.{table} SET workspace_id = :workspace_id "
                    "WHERE project_id = :project_id"
                ),
                {"workspace_id": workspace_by_project[project], "project_id": project},
            )

        op.alter_column(table, "workspace_id", nullable=False, schema=SCHEMA)

    for name, table, columns in WORKSPACE_INDEXES:
        op.create_index(name, table, columns, schema=SCHEMA)
    op.drop_index(OLD_ALERT_INDEX, table_name="alerts", schema=SCHEMA)


def downgrade() -> None:
    op.create_index(
        OLD_ALERT_INDEX,
        "alerts",
        ["project_id", "status", "last_triggered_at"],
        schema=SCHEMA,
    )
    for name, table, _ in reversed(WORKSPACE_INDEXES):
        op.drop_index(name, table_name=table, schema=SCHEMA)
    for table in reversed(TABLES):
        op.drop_column(table, "workspace_id", schema=SCHEMA)
