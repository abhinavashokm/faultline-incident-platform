"""create metric_buckets and processed_batches

Revision ID: c2a7f539d01e
Revises: b4f4062b5f0f
Create Date: 2026-11-12 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c2a7f539d01e'
down_revision: Union[str, Sequence[str], None] = 'b4f4062b5f0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'metric_buckets',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('environment', sa.String(length=100), nullable=False),
        sa.Column('service', sa.String(length=100), server_default='', nullable=False),
        sa.Column('route_template', sa.String(length=500), nullable=False),
        sa.Column('http_method', sa.String(length=10), nullable=False),
        sa.Column('release', sa.String(length=150), server_default='unknown', nullable=False),
        sa.Column('bucket_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('request_count', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('error_count', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('status_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('latency_histogram', postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column('histogram_version', sa.SmallInteger(), server_default='1', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint(
            'project_id', 'environment', 'service', 'route_template', 'http_method', 'release', 'bucket_start',
            name='metric_buckets_pkey'
        ),
        schema='processing'
    )
    op.create_index(
        'metric_buckets_release_comparison_idx',
        'metric_buckets',
        ['project_id', 'release', 'environment', 'bucket_start'],
        unique=False,
        schema='processing'
    )
    op.create_index(
        'metric_buckets_project_bucket_idx',
        'metric_buckets',
        ['project_id', 'bucket_start'],
        unique=False,
        schema='processing'
    )

    op.create_table(
        'processed_batches',
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('batch_id', name='processed_batches_pkey'),
        schema='processing'
    )
    op.create_index(
        'processed_batches_processed_at_idx',
        'processed_batches',
        ['processed_at'],
        unique=False,
        schema='processing'
    )


def downgrade() -> None:
    op.drop_index('processed_batches_processed_at_idx', table_name='processed_batches', schema='processing')
    op.drop_table('processed_batches', schema='processing')
    op.drop_index('metric_buckets_project_bucket_idx', table_name='metric_buckets', schema='processing')
    op.drop_index('metric_buckets_release_comparison_idx', table_name='metric_buckets', schema='processing')
    op.drop_table('metric_buckets', schema='processing')
