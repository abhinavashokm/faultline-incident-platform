from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.db import Base


class MetricBucket(Base):
    """Stores aggregated endpoint metrics partitioned into fixed 1-minute buckets."""

    __tablename__ = "metric_buckets"
    __table_args__ = (
        PrimaryKeyConstraint(
            "project_id",
            "environment",
            "service",
            "route_template",
            "http_method",
            "release",
            "bucket_start",
            name="metric_buckets_pkey",
        ),
        Index(
            "metric_buckets_release_comparison_idx",
            "project_id",
            "release",
            "environment",
            "bucket_start",
        ),
        Index("metric_buckets_project_bucket_idx", "project_id", "bucket_start"),
        {"schema": settings.database_schema},
    )

    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    environment: Mapped[str] = mapped_column(String(100), nullable=False)
    service: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")
    route_template: Mapped[str] = mapped_column(String(500), nullable=False)
    http_method: Mapped[str] = mapped_column(String(10), nullable=False)
    release: Mapped[str] = mapped_column(
        String(150), nullable=False, server_default="unknown"
    )
    bucket_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    request_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    error_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    status_counts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    latency_histogram: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False
    )
    histogram_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ProcessedBatch(Base):
    """Tracks SDK performance batches processed for deduplication / idempotency."""

    __tablename__ = "processed_batches"
    __table_args__ = (
        Index("processed_batches_processed_at_idx", "processed_at"),
        {"schema": settings.database_schema},
    )

    batch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True
    )
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
