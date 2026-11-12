from collections import defaultdict
from datetime import datetime, timezone
import threading
from typing import Any
import uuid

from faultline._internal import logger
from faultline.client import Client, get_client
from faultline.constants import CURRENT_HISTOGRAM_VERSION, HISTOGRAM_V1


def get_histogram_bucket_index(duration_ms: float, buckets: list[float] | tuple[float, ...] = HISTOGRAM_V1) -> int:
    """Find bucket index for a duration in milliseconds against upper bounds."""
    for idx, upper_bound in enumerate(buckets):
        if duration_ms <= upper_bound:
            return idx
    return len(buckets) - 1


class PerformanceBatcher:
    """Thread-safe batcher for application endpoint performance telemetry with histogram aggregation."""

    def __init__(
        self,
        batch_size: int = 50,
        max_buffer_size: int = 500,
        flush_interval: float = 10.0,
        client: Client | None = None,
    ) -> None:
        self.batch_size = batch_size
        self.max_buffer_size = max_buffer_size
        self.flush_interval = flush_interval
        self._default_client = client

        self._lock = threading.Lock()
        # buffer key: (method, route_template, release, environment, service)
        # buffer value: {
        #     "request_count": int,
        #     "error_count": int,
        #     "status_counts": dict[str, int],
        #     "latency_histogram": list[int],
        # }
        self._buffer: dict[tuple[str, str, str | None, str, str | None], dict[str, Any]] = {}
        self._total_records: int = 0
        self._interval_start: datetime | None = None

        self._timer: threading.Timer | None = None
        self._is_closed: bool = False
        self._schedule_timer()

    def _schedule_timer(self) -> None:
        if self._is_closed or self.flush_interval <= 0:
            return
        self._timer = threading.Timer(self.flush_interval, self._on_timer)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _on_timer(self) -> None:
        try:
            self.flush(client=self._default_client)
        except Exception as exc:
            logger.error("Error during scheduled performance flush: %s", exc)
        finally:
            with self._lock:
                if not self._is_closed:
                    self._schedule_timer()

    def record(
        self,
        method: str,
        route_template: str | None,
        status_code: int,
        duration: float,
        client: Client | None = None,
    ) -> None:
        """Record an endpoint request metric, aggregate in-memory, and trigger flush if batch size met."""
        target_client = client or self._default_client or get_client()
        if target_client is None:
            return
        if self._default_client is None and client is not None:
            self._default_client = client

        normalized_method = method.upper() if method else "GET"
        normalized_route = route_template or "unknown"
        release = target_client.config.release
        environment = target_client.config.environment
        service = target_client.config.service

        key = (normalized_method, normalized_route, release, environment, service)

        # Duration is passed in seconds; convert to milliseconds for histogram bucketing
        duration_ms = duration * 1000.0
        bucket_idx = get_histogram_bucket_index(duration_ms, HISTOGRAM_V1)
        is_error = 1 if status_code >= 500 else 0
        status_str = str(status_code)
        now_dt = datetime.now(timezone.utc)

        should_flush = False
        with self._lock:
            if self._is_closed:
                return

            if self._interval_start is None:
                self._interval_start = now_dt

            if key not in self._buffer:
                if len(self._buffer) >= self.max_buffer_size:
                    logger.warning("Faultline performance buffer is full; dropping record.")
                    return
                self._buffer[key] = {
                    "request_count": 0,
                    "error_count": 0,
                    "status_counts": defaultdict(int),
                    "latency_histogram": [0] * len(HISTOGRAM_V1),
                }

            entry = self._buffer[key]
            entry["request_count"] += 1
            entry["error_count"] += is_error
            entry["status_counts"][status_str] += 1
            entry["latency_histogram"][bucket_idx] += 1

            self._total_records += 1
            if self._total_records >= self.batch_size:
                should_flush = True

        if should_flush:
            self.flush(client=target_client)

    def flush(self, client: Client | None = None) -> bool:
        """Flush current aggregated metrics as a batch via the transport."""
        target_client = client or self._default_client or get_client()
        if target_client is None:
            return True

        now_dt = datetime.now(timezone.utc)
        with self._lock:
            if not self._buffer:
                return True

            items_to_send = list(self._buffer.items())
            self._buffer.clear()
            self._total_records = 0
            interval_start_dt = self._interval_start or now_dt
            self._interval_start = None

        interval_start_iso = interval_start_dt.isoformat()
        interval_end_iso = now_dt.isoformat()

        # Group metrics by (environment, release, service) if multiple exist, or construct batch
        # Typically environment/release/service match target_client.config
        metrics_payload = []
        for (m, r, rel, env, s), agg in items_to_send:
            metrics_payload.append({
                "route": r,
                "method": m,
                "request_count": agg["request_count"],
                "error_count": agg["error_count"],
                "status_counts": dict(agg["status_counts"]),
                "histogram_version": CURRENT_HISTOGRAM_VERSION,
                "latency_histogram": agg["latency_histogram"],
            })

        batch_payload = {
            "batch_id": str(uuid.uuid4()),
            "environment": target_client.config.environment,
            "release": target_client.config.release or "unknown",
            "service": target_client.config.service or "",
            "interval_start": interval_start_iso,
            "interval_end": interval_end_iso,
            "metrics": metrics_payload,
        }

        try:
            return target_client.transport.send(
                batch_payload,
                url=target_client.config.dsn.performance_url,
            )
        except Exception as exc:
            logger.error("Failed to enqueue performance batch: %s", exc)
            return False

    def close(self, client: Client | None = None) -> None:
        """Stop background flush timer and flush remaining aggregated metrics."""
        with self._lock:
            self._is_closed = True
            self._cancel_timer()
        self.flush(client=client)


_GLOBAL_BATCHER = PerformanceBatcher()


def record_request(
    method: str,
    route_template: str | None,
    status_code: int,
    duration: float,
    client: Client | None = None,
) -> None:
    """Record an endpoint request metric into the global performance batcher."""
    _GLOBAL_BATCHER.record(
        method=method,
        route_template=route_template,
        status_code=status_code,
        duration=duration,
        client=client,
    )


def flush_performance_batch(client: Client | None = None) -> bool:
    """Flush pending performance records into the transport queue."""
    return _GLOBAL_BATCHER.flush(client=client)


def close_performance_batcher(client: Client | None = None) -> None:
    """Close the global performance batcher and flush pending metrics."""
    _GLOBAL_BATCHER.close(client=client)
