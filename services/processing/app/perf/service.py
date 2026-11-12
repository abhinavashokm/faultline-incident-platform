import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.messaging.consumer import PermanentError
from app.perf.histograms import HISTOGRAM_BUCKETS
from app.perf.math import calculate_error_rate, compute_percentile
from app.perf.repository import PerfRepository
from app.perf.schemas import (
    EndpointDetailResponse,
    EndpointListItem,
    EndpointsListResponse,
    EndpointSummary,
    EventEnvelope,
    LatencyDistributionItem,
    NormalizedPerformanceBatch,
    ReleasePerformanceItem,
    RouteMetric,
)

logger = logging.getLogger(__name__)

SUPPORTED_HISTOGRAM_VERSION: int = 1


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
    """Business logic for performance metric processing, query aggregation, and transaction boundaries."""

    def __init__(
        self,
        session_or_factory: Any,
    ) -> None:
        if isinstance(session_or_factory, async_sessionmaker):
            self.session_factory = session_or_factory
            self.session = None
        elif isinstance(session_or_factory, AsyncSession):
            self.session_factory = None
            self.session = session_or_factory
        else:
            # Could be a mock or custom callable
            self.session_factory = session_or_factory
            self.session = session_or_factory

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
                "Batch %s interval crosses minute boundary: start=%s, end=%s",
                payload.batch_id,
                payload.interval_start,
                payload.interval_end,
            )

        if not payload.metrics:
            logger.info("Batch %s has no metrics, marking as processed", payload.batch_id)
            if self.session_factory is not None:
                async with self.session_factory() as session:
                    async with session.begin():
                        repo = PerfRepository(session)
                        is_new = await repo.record_batch_if_new(
                            batch_id=payload.batch_id,
                            workspace_id=envelope.workspace_id,
                            project_id=envelope.project_id,
                        )
                        return ProcessedBatchResult(
                            batch_id=payload.batch_id,
                            project_id=envelope.project_id,
                            workspace_id=envelope.workspace_id,
                            is_duplicate=not is_new,
                            metrics_count=0,
                        )

        # Pre-aggregate duplicate routes in the incoming batch
        aggregated_metrics = pre_aggregate_metrics(payload.metrics)

        if self.session_factory is None:
            raise RuntimeError("session_factory is required for process_batch")

        async with self.session_factory() as session:
            async with session.begin():
                repo = PerfRepository(session)

                is_new = await repo.record_batch_if_new(
                    batch_id=payload.batch_id,
                    workspace_id=envelope.workspace_id,
                    project_id=envelope.project_id,
                )
                if not is_new:
                    logger.info(
                        "Batch %s for project %s already processed. Skipping duplicate.",
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

                for metric in aggregated_metrics:
                    item_dict = {
                        "workspace_id": envelope.workspace_id,
                        "project_id": envelope.project_id,
                        "environment": payload.environment,
                        "service": "",  # Default service
                        "route_template": metric.route,
                        "http_method": metric.method,
                        "release": payload.release,
                        "bucket_start": bucket_start,
                        "request_count": metric.request_count,
                        "error_count": metric.error_count,
                        "status_counts": json.dumps(metric.status_counts) if metric.status_counts else None,
                        "latency_histogram": metric.latency_histogram,
                        "histogram_version": metric.histogram_version,
                    }
                    await repo.upsert_metric_bucket(item_dict)

                logger.info(
                    "Successfully processed batch %s with %d metrics for project %s",
                    payload.batch_id,
                    len(aggregated_metrics),
                    envelope.project_id,
                )
                return ProcessedBatchResult(
                    batch_id=payload.batch_id,
                    project_id=envelope.project_id,
                    workspace_id=envelope.workspace_id,
                    is_duplicate=False,
                    metrics_count=len(aggregated_metrics),
                )

    # -----------------------------------------------------------------------
    # HTTP Read Methods
    # -----------------------------------------------------------------------

    async def list_endpoints(
        self,
        workspace_id: UUID,
        project_id: UUID,
        from_time: datetime,
        to_time: datetime,
        environment: str | None = None,
        release: str | None = None,
    ) -> EndpointsListResponse:
        """List aggregated performance metrics for all endpoints in the given time range."""
        if self.session is None:
            raise RuntimeError("AsyncSession is required for HTTP read methods")

        repo = PerfRepository(self.session)
        boundaries = HISTOGRAM_BUCKETS[SUPPORTED_HISTOGRAM_VERSION]

        raw_metrics = await repo.list_endpoints_metrics(
            workspace_id=workspace_id,
            project_id=project_id,
            from_time=from_time,
            to_time=to_time,
            histogram_version=SUPPORTED_HISTOGRAM_VERSION,
            environment=environment,
            release=release,
        )

        items: list[EndpointListItem] = []
        for r in raw_metrics:
            req_count = r["request_count"]
            err_count = r["error_count"]
            hist = r["histogram"]
            error_rate = calculate_error_rate(err_count, req_count)
            p50 = compute_percentile(hist, 0.50, boundaries)
            p95 = compute_percentile(hist, 0.95, boundaries)
            p99 = compute_percentile(hist, 0.99, boundaries)

            items.append(
                EndpointListItem(
                    route=r["route"],
                    method=r["method"],
                    requests=req_count,
                    error_rate=error_rate,
                    p50_ms=p50,
                    p95_ms=p95,
                    p99_ms=p99,
                )
            )

        # Sort by: p95 desc, tiebreak route asc, then method asc
        # If p95 is None, treat as -1 so it sorts at the end
        items.sort(
            key=lambda item: (
                -(item.p95_ms if item.p95_ms is not None else -1),
                item.route,
                item.method,
            )
        )

        total = len(items)
        truncated = total > 500
        capped_items = items[:500]

        return EndpointsListResponse(
            items=capped_items,
            total=total,
            truncated=truncated,
        )

    async def get_endpoint_detail(
        self,
        workspace_id: UUID,
        project_id: UUID,
        route: str,
        method: str,
        from_time: datetime,
        to_time: datetime,
        environment: str | None = None,
        release: str | None = None,
    ) -> EndpointDetailResponse:
        """Get detailed performance breakdown for a single route + method."""
        if self.session is None:
            raise RuntimeError("AsyncSession is required for HTTP read methods")

        repo = PerfRepository(self.session)
        boundaries = HISTOGRAM_BUCKETS[SUPPORTED_HISTOGRAM_VERSION]

        summary_data = await repo.get_endpoint_summary_and_distribution(
            workspace_id=workspace_id,
            project_id=project_id,
            route=route,
            method=method,
            from_time=from_time,
            to_time=to_time,
            histogram_version=SUPPORTED_HISTOGRAM_VERSION,
            environment=environment,
            release=release,
        )

        if summary_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not found",
            )

        req_count = summary_data["request_count"]
        err_count = summary_data["error_count"]
        hist = summary_data["histogram"]

        summary = EndpointSummary(
            request_count=req_count,
            error_rate=calculate_error_rate(err_count, req_count),
            p50_ms=compute_percentile(hist, 0.50, boundaries),
            p95_ms=compute_percentile(hist, 0.95, boundaries),
            p99_ms=compute_percentile(hist, 0.99, boundaries),
        )

        latency_distribution: list[LatencyDistributionItem] = []
        for i, bound in enumerate(boundaries):
            count = hist[i] if i < len(hist) else 0
            le_ms = None if math.isinf(bound) else int(bound)
            latency_distribution.append(
                LatencyDistributionItem(le_ms=le_ms, count=count)
            )

        status_counts = await repo.get_endpoint_status_counts(
            workspace_id=workspace_id,
            project_id=project_id,
            route=route,
            method=method,
            from_time=from_time,
            to_time=to_time,
            histogram_version=SUPPORTED_HISTOGRAM_VERSION,
            environment=environment,
            release=release,
        )

        raw_releases = await repo.get_endpoint_releases(
            workspace_id=workspace_id,
            project_id=project_id,
            route=route,
            method=method,
            from_time=from_time,
            to_time=to_time,
            histogram_version=SUPPORTED_HISTOGRAM_VERSION,
            environment=environment,
        )

        releases: list[ReleasePerformanceItem] = []
        for rel in raw_releases:
            rel_req = rel["request_count"]
            rel_err = rel["error_count"]
            rel_hist = rel["histogram"]
            releases.append(
                ReleasePerformanceItem(
                    release=rel["release"],
                    requests=rel_req,
                    error_rate=calculate_error_rate(rel_err, rel_req),
                    p95_ms=compute_percentile(rel_hist, 0.95, boundaries),
                )
            )

        return EndpointDetailResponse(
            summary=summary,
            latency_distribution=latency_distribution,
            status_counts=status_counts,
            releases=releases,
        )
