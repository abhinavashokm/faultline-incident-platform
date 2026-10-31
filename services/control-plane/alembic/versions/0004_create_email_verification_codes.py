"""create email verification codes table

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="email_verification_codes_attempts_ck"),
        sa.CheckConstraint("expires_at > created_at", name="email_verification_codes_expires_at_ck"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["control.users.id"],
            ondelete="CASCADE",
            name="email_verification_codes_user_fk",
        ),
        sa.PrimaryKeyConstraint("id", name="email_verification_codes_pkey"),
        schema="control",
    )
    op.create_index(
        "email_verification_codes_user_id_active_uq",
        "email_verification_codes",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("consumed_at IS NULL"),
        schema="control",
    )
    op.create_index(
        "email_verification_codes_expires_at_idx",
        "email_verification_codes",
        ["expires_at"],
        unique=False,
        schema="control",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "email_verification_codes_expires_at_idx",
        table_name="email_verification_codes",
        schema="control",
    )
    op.drop_index(
        "email_verification_codes_user_id_active_uq",
        table_name="email_verification_codes",
        schema="control",
    )
    op.drop_table("email_verification_codes", schema="control")

