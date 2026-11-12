import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.messaging.consumer import PermanentError
from app.perf.histograms import HISTOGRAM_BUCKETS
from app.perf.repository import PerfRepository
from app.perf.schemas import EventEnvelope, NormalizedPerformanceBatch, RouteMetric

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessedBatchResult:
    batch_id: UUID
    project_id: UUID
    workspace_id: UUID
    is_duplicate: bool
    metrics_count: int


def pre_aggregate_metrics(
    metrics: list[RouteMetric],
) -> list[RouteMetric]:
    """Pre-aggregate metrics within the same batch sharing the same endpoint key.

    Avoids PostgreSQL 'ON CONFLICT DO UPDATE command cannot affect row a second time'.
    """
    if not metrics:
        return []

    grouped: dict[tuple[str, str, int], dict[str, Any]] = {}

    for m in metrics:
        key = (m.route, m.method, m.histogram_version)
        if key not in grouped:
            grouped[key] = {
                "route": m.route,
                "method": m.method,
                "request_count": m.request_count,
                "error_count": m.error_count,
                "status_counts": defaultdict(int, m.status_counts),
                "histogram_version": m.histogram_version,
                "latency_histogram": list(m.latency_histogram),
            }
        else:
            accum = grouped[key]
            accum["request_count"] += m.request_count
            accum["error_count"] += m.error_count
            for status_code, count in m.status_counts.items():
                accum["status_counts"][str(status_code)] += count
            for i, count in enumerate(m.latency_histogram):
                accum["latency_histogram"][i] += count

    aggregated: list[RouteMetric] = []
    for data in grouped.values():
        aggregated.append(
            RouteMetric(
                route=data["route"],
                method=data["method"],
                request_count=data["request_count"],
                error_count=data["error_count"],
                status_counts=dict(data["status_counts"]),
                histogram_version=data["histogram_version"],
                latency_histogram=data["latency_histogram"],
            )
        )

    return aggregated


class PerfService:
    """Business logic for performance metric processing and transaction boundaries."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def process_batch(
        self,
        envelope: EventEnvelope[NormalizedPerformanceBatch],
    ) -> ProcessedBatchResult:
        payload = envelope.payload

        # Truncate interval_start down to the nearest minute in UTC
        start = payload.interval_start
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        else:
            start = start.astimezone(timezone.utc)

        bucket_start = start.replace(second=0, microsecond=0)

        # Check if interval_end crosses into the next minute and log warning
        end = payload.interval_end
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        else:
            end = end.astimezone(timezone.utc)

        if end.replace(second=0, microsecond=0) > bucket_start:
            logger.warning(
                "Batch interval crosses minute boundary: interval_start=%s interval_end=%s batch_id=%s. Attributing to bucket_start=%s",
                payload.interval_start.isoformat(),
                payload.interval_end.isoformat(),
                payload.batch_id,
                bucket_start.isoformat(),
            )

        # Pre-aggregate duplicate routes in the same batch
        merged_metrics = pre_aggregate_metrics(payload.metrics)

        # Sort items deterministically by primary key to avoid deadlocks:
        # PK: (project_id, environment, service, route_template, http_method, release, bucket_start)
        service_name = ""
        environment = payload.environment
        release = payload.release

        sorted_metrics = sorted(
            merged_metrics,
            key=lambda m: (
                envelope.project_id,
                environment,
                service_name,
                m.route,
                m.method,
                release,
                bucket_start,
            ),
        )

        async with self.session_factory() as session:
            async with session.begin():
                repo = PerfRepository(session)

                # 1. Idempotency check via processed_batches
                is_new = await repo.record_batch_if_new(
                    batch_id=payload.batch_id,
                    workspace_id=envelope.workspace_id,
                    project_id=envelope.project_id,
                )

                if not is_new:
                    logger.info(
                        "Batch already processed (idempotent duplicate skipped): batch_id=%s project_id=%s",
                        payload.batch_id,
                        envelope.project_id,
                    )
                    return ProcessedBatchResult(
                        batch_id=payload.batch_id,
                        project_id=envelope.project_id,
                        workspace_id=envelope.workspace_id,
                        is_duplicate=True,
                        metrics_count=0,
                    )

                # 2. Upsert each metric bucket
                for m in sorted_metrics:
                    row_data = {
                        "workspace_id": envelope.workspace_id,
                        "project_id": envelope.project_id,
                        "environment": environment,
                        "service": service_name,
                        "route_template": m.route,
                        "http_method": m.method,
                        "release": release,
                        "bucket_start": bucket_start,
                        "request_count": m.request_count,
                        "error_count": m.error_count,
                        "status_counts": json.dumps(m.status_counts),
                        "latency_histogram": m.latency_histogram,
                        "histogram_version": m.histogram_version,
                    }
                    await repo.upsert_metric_bucket(row_data)

        logger.info(
            "Batch processed successfully: batch_id=%s project_id=%s workspace_id=%s metrics_upserted=%d bucket_start=%s",
            payload.batch_id,
            envelope.project_id,
            envelope.workspace_id,
            len(sorted_metrics),
            bucket_start.isoformat(),
        )

        return ProcessedBatchResult(
            batch_id=payload.batch_id,
            project_id=envelope.project_id,
            workspace_id=envelope.workspace_id,
            is_duplicate=False,
            metrics_count=len(sorted_metrics),
        )
