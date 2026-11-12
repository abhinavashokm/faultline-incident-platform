import logging
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
