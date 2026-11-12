import json
import logging
from collections.abc import Awaitable, Callable

from app.messaging.consumer import PermanentError
from app.perf.schemas import EventEnvelope, NormalizedPerformanceBatch
from app.perf.service import PerfService

logger = logging.getLogger(__name__)


def parse_and_validate_performance_message(raw: bytes) -> EventEnvelope[NormalizedPerformanceBatch]:
    """Parse raw Kafka bytes and validate against EventEnvelope[NormalizedPerformanceBatch].

    Raises PermanentError on bad messages (invalid JSON, missing envelope fields,
    unsupported schema version, validation errors, event_id/batch_id mismatch).
    """
    try:
        data = json.loads(raw)
    except Exception as exc:
        # TODO: Route exhausted or bad messages to performance-metrics-dlq once DLQ infrastructure is enabled.
        raise PermanentError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        # TODO: Route bad messages to performance-metrics-dlq.
        raise PermanentError("Message payload must be a JSON object")

    if "schema_version" not in data:
        # TODO: Route bad messages to performance-metrics-dlq.
        raise PermanentError("Legacy flat message rejected: missing 'schema_version'")

    schema_version = data.get("schema_version")
    if schema_version != 1:
        # TODO: Route bad messages to performance-metrics-dlq.
        raise PermanentError(
            f"Unsupported schema_version: {schema_version} (only version 1 is supported)"
        )

    for field in ("event_id", "workspace_id", "project_id", "received_at", "payload"):
        if field not in data or data[field] is None:
            # TODO: Route bad messages to performance-metrics-dlq.
            raise PermanentError(f"Missing required envelope field: {field}")

    if not isinstance(data.get("payload"), dict):
        # TODO: Route bad messages to performance-metrics-dlq.
        raise PermanentError("Envelope 'payload' must be a JSON object")

    try:
        envelope = EventEnvelope[NormalizedPerformanceBatch].model_validate(data)
    except Exception as exc:
        # TODO: Route bad messages to performance-metrics-dlq.
        raise PermanentError(f"Envelope validation failed: {exc}") from exc

    # Enforce envelope event_id matches payload batch_id
    if str(envelope.event_id) != str(envelope.payload.batch_id):
        # TODO: Route bad messages to performance-metrics-dlq.
        raise PermanentError(
            f"Envelope event_id ({envelope.event_id}) does not match payload batch_id ({envelope.payload.batch_id})"
        )

    return envelope


def build_perf_handler(
    service: PerfService,
) -> Callable[[bytes, str, int, int], Awaitable[None]]:
    """Build message handler for performance consumer."""

    async def handler(raw: bytes, topic: str, partition: int, offset: int) -> None:
        envelope = parse_and_validate_performance_message(raw)
        result = await service.process_batch(envelope)

        logger.info(
            "Performance batch processed: batch_id=%s project_id=%s is_duplicate=%s metrics_count=%d topic=%s partition=%d offset=%d",
            result.batch_id,
            result.project_id,
            result.is_duplicate,
            result.metrics_count,
            topic,
            partition,
            offset,
        )

    return handler
