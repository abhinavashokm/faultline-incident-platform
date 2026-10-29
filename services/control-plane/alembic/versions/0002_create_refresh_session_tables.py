"""create refresh session tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=30), nullable=True),
        sa.CheckConstraint(
            "revoked_reason IS NULL OR revoked_reason IN ('logout', 'reuse_detected', 'user_disabled')",
            name="refresh_sessions_revoked_reason_ck",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["control.users.id"],
            ondelete="CASCADE",
            name="refresh_sessions_user_fk",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="control",
    )
    op.create_index(
        "refresh_sessions_user_id_idx",
        "refresh_sessions",
        ["user_id"],
        unique=False,
        schema="control",
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["control.refresh_sessions.id"],
            ondelete="CASCADE",
            name="refresh_tokens_session_fk",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="refresh_tokens_token_hash_uq"),
        schema="control",
    )
    op.create_index(
        "refresh_tokens_session_id_idx",
        "refresh_tokens",
        ["session_id"],
        unique=False,
        schema="control",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "refresh_tokens_session_id_idx",
        table_name="refresh_tokens",
        schema="control",
    )
    op.drop_table("refresh_tokens", schema="control")
    op.drop_index(
        "refresh_sessions_user_id_idx",
        table_name="refresh_sessions",
        schema="control",
    )
    op.drop_table("refresh_sessions", schema="control")

