import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.messaging.consumer import PermanentError
from app.perf.models import MetricBucket, ProcessedBatch

logger = logging.getLogger(__name__)


class PerfRepository:
    """Database operations for performance metrics and batch idempotency tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_batch_if_new(
        self,
        batch_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
    ) -> bool:
        """Insert batch_id into processed_batches using ON CONFLICT DO NOTHING.

        Returns True if the batch was newly inserted, or False if it already existed.
        """
        stmt = (
            insert(ProcessedBatch)
            .values(
                batch_id=batch_id,
                workspace_id=workspace_id,
                project_id=project_id,
            )
            .on_conflict_do_nothing(index_elements=["batch_id"])
        )
        result = await self.session.execute(stmt)
        return bool(result.rowcount > 0)

    async def upsert_metric_bucket(self, item: dict[str, Any]) -> None:
        """Upsert a single metric bucket row into processing.metric_buckets.

        Uses ON CONFLICT DO UPDATE with pure SQL array element-wise sum for latency_histogram
        and jsonb key-by-key sum for status_counts. Enforces WHERE metric_buckets.histogram_version = EXCLUDED.histogram_version.
        Raises PermanentError if histogram_version does not match the existing row.
        """
        table_name = f"{settings.database_schema}.metric_buckets"

        sql_stmt = text(f"""
            INSERT INTO {table_name} (
                workspace_id,
                project_id,
                environment,
                service,
                route_template,
                http_method,
                release,
                bucket_start,
                request_count,
                error_count,
                status_counts,
                latency_histogram,
                histogram_version,
                updated_at
            ) VALUES (
                :workspace_id,
                :project_id,
                :environment,
                :service,
                :route_template,
                :http_method,
                :release,
                :bucket_start,
                :request_count,
                :error_count,
                CAST(:status_counts AS jsonb),
                CAST(:latency_histogram AS bigint[]),
                :histogram_version,
                NOW()
            )
            ON CONFLICT (project_id, environment, service, route_template, http_method, release, bucket_start)
            DO UPDATE SET
                request_count = {table_name}.request_count + EXCLUDED.request_count,
                error_count = {table_name}.error_count + EXCLUDED.error_count,
                latency_histogram = (
                    SELECT array_agg(a + b ORDER BY i)
                    FROM unnest({table_name}.latency_histogram, EXCLUDED.latency_histogram)
                         WITH ORDINALITY AS t(a, b, i)
                ),
                status_counts = COALESCE(
                    (
                        SELECT jsonb_object_agg(
                            key,
                            COALESCE(curr_val, 0) + COALESCE(new_val, 0)
                        )
                        FROM (
                            SELECT key,
                                   MAX(CASE WHEN src = 1 THEN val END) AS curr_val,
                                   MAX(CASE WHEN src = 2 THEN val END) AS new_val
                            FROM (
                                SELECT key, value::bigint AS val, 1 AS src
                                FROM jsonb_each_text(COALESCE({table_name}.status_counts, '{{}}'::jsonb))
                                UNION ALL
                                SELECT key, value::bigint AS val, 2 AS src
                                FROM jsonb_each_text(COALESCE(EXCLUDED.status_counts, '{{}}'::jsonb))
                            ) raw_counts
                            GROUP BY key
                        ) aggregated_counts
                    ),
                    '{{}}'::jsonb
                ),
                updated_at = NOW()
            WHERE {table_name}.histogram_version = EXCLUDED.histogram_version
        """)

        result = await self.session.execute(sql_stmt, item)

        if result.rowcount == 0:
            # Row was not inserted and not updated. Check if row exists with a different histogram_version
            existing_query = select(MetricBucket.histogram_version).where(
                MetricBucket.project_id == item["project_id"],
                MetricBucket.environment == item["environment"],
                MetricBucket.service == item["service"],
                MetricBucket.route_template == item["route_template"],
                MetricBucket.http_method == item["http_method"],
                MetricBucket.release == item["release"],
                MetricBucket.bucket_start == item["bucket_start"],
            )
            existing_res = await self.session.execute(existing_query)
            existing_version = existing_res.scalar_one_or_none()

            if existing_version is not None and existing_version != item["histogram_version"]:
                raise PermanentError(
                    f"Histogram version mismatch for route={item['route_template']}: "
                    f"existing row has version {existing_version}, incoming has version {item['histogram_version']}. "
                    "Cannot merge different histogram versions."
                )

    async def list_endpoints_metrics(
        self,
        workspace_id: UUID,
        project_id: UUID,
        from_time: datetime,
        to_time: datetime,
        histogram_version: int,
        environment: str | None = None,
        release: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aggregate metric bucket counts grouped by route_template and http_method across service.

        Sums requests, errors, and each histogram bucket (1 through 6).
        """
        table_name = f"{settings.database_schema}.metric_buckets"

        where_clauses = [
            "workspace_id = :workspace_id",
            "project_id = :project_id",
            "bucket_start >= :from_time",
            "bucket_start < :to_time",
            "histogram_version = :histogram_version",
        ]
        params: dict[str, Any] = {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "from_time": from_time,
            "to_time": to_time,
            "histogram_version": histogram_version,
        }

        if environment is not None:
            where_clauses.append("environment = :environment")
            params["environment"] = environment

        if release is not None:
            where_clauses.append("release = :release")
            params["release"] = release

        where_sql = " AND ".join(where_clauses)

        sql_stmt = text(f"""
            SELECT
                route_template AS route,
                http_method AS method,
                COALESCE(SUM(request_count), 0)::bigint AS request_count,
                COALESCE(SUM(error_count), 0)::bigint AS error_count,
                COALESCE(SUM(latency_histogram[1]), 0)::bigint AS b1,
                COALESCE(SUM(latency_histogram[2]), 0)::bigint AS b2,
                COALESCE(SUM(latency_histogram[3]), 0)::bigint AS b3,
                COALESCE(SUM(latency_histogram[4]), 0)::bigint AS b4,
                COALESCE(SUM(latency_histogram[5]), 0)::bigint AS b5,
                COALESCE(SUM(latency_histogram[6]), 0)::bigint AS b6
            FROM {table_name}
            WHERE {where_sql}
            GROUP BY route_template, http_method
        """)

        result = await self.session.execute(sql_stmt, params)
        rows = []
        for r in result.mappings():
            rows.append({
                "route": r["route"],
                "method": r["method"],
                "request_count": int(r["request_count"]),
                "error_count": int(r["error_count"]),
                "histogram": [
                    int(r["b1"]),
                    int(r["b2"]),
                    int(r["b3"]),
                    int(r["b4"]),
                    int(r["b5"]),
                    int(r["b6"]),
                ],
            })
        return rows

    async def get_endpoint_summary_and_distribution(
        self,
        workspace_id: UUID,
        project_id: UUID,
        route: str,
        method: str,
        from_time: datetime,
        to_time: datetime,
        histogram_version: int,
        environment: str | None = None,
        release: str | None = None,
    ) -> dict[str, Any] | None:
        """Aggregate summary metrics and latency histogram distribution for a specific route and method.

        Returns None if no matching rows exist.
        """
        table_name = f"{settings.database_schema}.metric_buckets"

        where_clauses = [
            "workspace_id = :workspace_id",
            "project_id = :project_id",
            "route_template = :route",
            "http_method = :method",
            "bucket_start >= :from_time",
            "bucket_start < :to_time",
            "histogram_version = :histogram_version",
        ]
        params: dict[str, Any] = {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "route": route,
            "method": method,
            "from_time": from_time,
            "to_time": to_time,
            "histogram_version": histogram_version,
        }

        if environment is not None:
            where_clauses.append("environment = :environment")
            params["environment"] = environment

        if release is not None:
            where_clauses.append("release = :release")
            params["release"] = release

        where_sql = " AND ".join(where_clauses)

        sql_stmt = text(f"""
            SELECT
                COUNT(*)::bigint AS match_count,
                COALESCE(SUM(request_count), 0)::bigint AS request_count,
                COALESCE(SUM(error_count), 0)::bigint AS error_count,
                COALESCE(SUM(latency_histogram[1]), 0)::bigint AS b1,
                COALESCE(SUM(latency_histogram[2]), 0)::bigint AS b2,
                COALESCE(SUM(latency_histogram[3]), 0)::bigint AS b3,
                COALESCE(SUM(latency_histogram[4]), 0)::bigint AS b4,
                COALESCE(SUM(latency_histogram[5]), 0)::bigint AS b5,
                COALESCE(SUM(latency_histogram[6]), 0)::bigint AS b6
            FROM {table_name}
            WHERE {where_sql}
        """)

        result = await self.session.execute(sql_stmt, params)
        row = result.mappings().one()

        if int(row["match_count"]) == 0:
            return None

        return {
            "request_count": int(row["request_count"]),
            "error_count": int(row["error_count"]),
            "histogram": [
                int(row["b1"]),
                int(row["b2"]),
                int(row["b3"]),
                int(row["b4"]),
                int(row["b5"]),
                int(row["b6"]),
            ],
        }

    async def get_endpoint_status_counts(
        self,
        workspace_id: UUID,
        project_id: UUID,
        route: str,
        method: str,
        from_time: datetime,
        to_time: datetime,
        histogram_version: int,
        environment: str | None = None,
        release: str | None = None,
    ) -> dict[str, int]:
        """Aggregate status code counts for a route and method using jsonb_each_text lateral unnesting.

        Implicit lateral join drops rows with NULL status_counts.
        """
        table_name = f"{settings.database_schema}.metric_buckets"

        where_clauses = [
            "mb.workspace_id = :workspace_id",
            "mb.project_id = :project_id",
            "mb.route_template = :route",
            "mb.http_method = :method",
            "mb.bucket_start >= :from_time",
            "mb.bucket_start < :to_time",
            "mb.histogram_version = :histogram_version",
        ]
        params: dict[str, Any] = {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "route": route,
            "method": method,
            "from_time": from_time,
            "to_time": to_time,
            "histogram_version": histogram_version,
        }

        if environment is not None:
            where_clauses.append("mb.environment = :environment")
            params["environment"] = environment

        if release is not None:
            where_clauses.append("mb.release = :release")
            params["release"] = release

        where_sql = " AND ".join(where_clauses)

        sql_stmt = text(f"""
            SELECT kv.key AS status_code, SUM(kv.value::bigint)::bigint AS cnt
            FROM {table_name} mb,
                 jsonb_each_text(CASE WHEN jsonb_typeof(mb.status_counts) = 'object' THEN mb.status_counts ELSE '{{}}'::jsonb END) AS kv
            WHERE {where_sql}
            GROUP BY kv.key
        """)

        result = await self.session.execute(sql_stmt, params)
        status_counts: dict[str, int] = {}
        for row in result.mappings():
            status_counts[str(row["status_code"])] = int(row["cnt"])
        return status_counts

    async def get_endpoint_releases(
        self,
        workspace_id: UUID,
        project_id: UUID,
        route: str,
        method: str,
        from_time: datetime,
        to_time: datetime,
        histogram_version: int,
        environment: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aggregate metrics per release for a route and method.

        Note: This query intentionally IGNORES the release filter, but respects environment.
        """
        table_name = f"{settings.database_schema}.metric_buckets"

        where_clauses = [
            "workspace_id = :workspace_id",
            "project_id = :project_id",
            "route_template = :route",
            "http_method = :method",
            "bucket_start >= :from_time",
            "bucket_start < :to_time",
            "histogram_version = :histogram_version",
        ]
        params: dict[str, Any] = {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "route": route,
            "method": method,
            "from_time": from_time,
            "to_time": to_time,
            "histogram_version": histogram_version,
        }

        if environment is not None:
            where_clauses.append("environment = :environment")
            params["environment"] = environment

        where_sql = " AND ".join(where_clauses)

        sql_stmt = text(f"""
            SELECT
                release,
                COALESCE(SUM(request_count), 0)::bigint AS request_count,
                COALESCE(SUM(error_count), 0)::bigint AS error_count,
                COALESCE(SUM(latency_histogram[1]), 0)::bigint AS b1,
                COALESCE(SUM(latency_histogram[2]), 0)::bigint AS b2,
                COALESCE(SUM(latency_histogram[3]), 0)::bigint AS b3,
                COALESCE(SUM(latency_histogram[4]), 0)::bigint AS b4,
                COALESCE(SUM(latency_histogram[5]), 0)::bigint AS b5,
                COALESCE(SUM(latency_histogram[6]), 0)::bigint AS b6
            FROM {table_name}
            WHERE {where_sql}
            GROUP BY release
            ORDER BY release ASC
        """)

        result = await self.session.execute(sql_stmt, params)
        rows = []
        for r in result.mappings():
            rows.append({
                "release": r["release"],
                "request_count": int(r["request_count"]),
                "error_count": int(r["error_count"]),
                "histogram": [
                    int(r["b1"]),
                    int(r["b2"]),
                    int(r["b3"]),
                    int(r["b4"]),
                    int(r["b5"]),
                    int(r["b6"]),
                ],
            })
        return rows
