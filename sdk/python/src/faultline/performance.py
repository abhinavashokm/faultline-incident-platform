from datetime import datetime, timezone
import threading
from typing import Any
import uuid

from faultline._internal import logger
from faultline.client import Client, get_client


class PerformanceBatcher:
    """Thread-safe batcher for application endpoint performance telemetry."""

    def __init__(self, batch_size: int = 50, max_buffer_size: int = 500) -> None:
        self.batch_size = batch_size
        self.max_buffer_size = max_buffer_size
        self._lock = threading.Lock()
        self._buffer: list[dict[str, Any]] = []

    def record(
        self,
        method: str,
        route_template: str | None,
        status_code: int,
        duration: float,
        client: Client | None = None,
    ) -> None:
        """Record an endpoint request metric and enqueue into the batch buffer."""
        target_client = client or get_client()
        if target_client is None:
            return

        now_utc = datetime.now(timezone.utc).isoformat()
        record_item = {
            "method": method.upper() if method else "GET",
            "route_template": route_template,
            "status": status_code,
            "duration": round(duration, 6),
            "release": target_client.config.release,
            "environment": target_client.config.environment,
            "service": target_client.config.service,
            "timestamp": now_utc,
        }

        should_flush = False
        with self._lock:
            if len(self._buffer) >= self.max_buffer_size:
                # Bounded buffer: drop newest and log warning
                logger.warning("Faultline performance buffer is full; dropping record.")
                return
            self._buffer.append(record_item)
            if len(self._buffer) >= self.batch_size:
                should_flush = True

        if should_flush:
            self.flush(client=target_client)

    def flush(self, client: Client | None = None) -> bool:
        """Flush the current buffered performance records as a batch via the transport."""
        target_client = client or get_client()
        if target_client is None:
            return True

        records_to_send: list[dict[str, Any]] = []
        with self._lock:
            if not self._buffer:
                return True
            records_to_send = list(self._buffer)
            self._buffer.clear()

        batch_payload = {
            "batch_id": str(uuid.uuid4()),
            "environment": target_client.config.environment,
            "release": target_client.config.release,
            "service": target_client.config.service,
            "interval_start": records_to_send[0]["timestamp"],
            "interval_end": records_to_send[-1]["timestamp"],
            "count": len(records_to_send),
            "records": records_to_send,
        }

        try:
            return target_client.transport.send(
                batch_payload,
                url=target_client.config.dsn.performance_url,
            )
        except Exception as exc:
            logger.error("Failed to enqueue performance batch: %s", exc)
            return False


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

