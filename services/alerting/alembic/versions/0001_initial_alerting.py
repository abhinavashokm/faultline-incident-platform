"""create initial alerting schema

Revision ID: 0001_initial_alerting
Revises: 
Create Date: 2026-11-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_alerting"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "alerting"


def upgrade() -> None:
    # 1. alert_rules
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recovery_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("severity", sa.String(length=30), nullable=False, server_default="warning"),
        sa.Column("environment", sa.String(length=100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("minimum_event_count", sa.Integer(), nullable=True),
        sa.Column("window_seconds", sa.Integer(), nullable=True),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_alert_rules_project_id",
        "alert_rules",
        ["project_id"],
        schema=SCHEMA,
    )

    # 2. alert_states
    op.create_table(
        "alert_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="normal"),
        sa.Column("first_triggered_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            [f"{SCHEMA}.alert_rules.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("rule_id", "deduplication_key", name="uq_alert_states_rule_dedup"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_alert_states_project_status",
        "alert_states",
        ["project_id", "status"],
        schema=SCHEMA,
    )

    # 3. alerts
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="firing"),
        sa.Column("occurrence_count", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("first_triggered_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("recovered_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            [f"{SCHEMA}.alert_rules.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["state_id"],
            [f"{SCHEMA}.alert_states.id"],
            ondelete="CASCADE",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_alerts_project_id",
        "alerts",
        ["project_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_alerts_state_id",
        "alerts",
        ["state_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_alerts_project_status_last_triggered",
        "alerts",
        ["project_id", "status", "last_triggered_at"],
        schema=SCHEMA,
    )

    # 4. notification_channels
    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("channel_type", sa.String(length=30), nullable=False),
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("secret_reference", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_notification_channels_project_id",
        "notification_channels",
        ["project_id"],
        schema=SCHEMA,
    )

    # 5. alert_rule_channels
    op.create_table(
        "alert_rule_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            [f"{SCHEMA}.alert_rules.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            [f"{SCHEMA}.notification_channels.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("rule_id", "channel_id", name="uq_alert_rule_channels"),
        schema=SCHEMA,
    )

    # 6. deliveries
    op.create_table(
        "deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            [f"{SCHEMA}.alerts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            [f"{SCHEMA}.notification_channels.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_deliveries_idempotency_key"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_deliveries_project_id",
        "deliveries",
        ["project_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_deliveries_status_next_attempt",
        "deliveries",
        ["status", "next_attempt_at"],
        schema=SCHEMA,
    )

    # 7. delivery_attempts
    op.create_table(
        "delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            [f"{SCHEMA}.deliveries.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("delivery_id", "attempt_number", name="uq_delivery_attempt_number"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("delivery_attempts", schema=SCHEMA)
    op.drop_table("deliveries", schema=SCHEMA)
    op.drop_table("alert_rule_channels", schema=SCHEMA)
    op.drop_table("notification_channels", schema=SCHEMA)
    op.drop_table("alerts", schema=SCHEMA)
    op.drop_table("alert_states", schema=SCHEMA)
    op.drop_table("alert_rules", schema=SCHEMA)
