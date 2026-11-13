"""create processed_events table

Revision ID: 0002_processed_events
Revises: 0001_initial_alerting
Create Date: 2026-11-13 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_processed_events"
down_revision: Union[str, None] = "0001_initial_alerting"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "alerting"


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_alerting_processed_events_processed_at",
        "processed_events",
        ["processed_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_alerting_processed_events_processed_at",
        table_name="processed_events",
        schema=SCHEMA,
    )
    op.drop_table("processed_events", schema=SCHEMA)
