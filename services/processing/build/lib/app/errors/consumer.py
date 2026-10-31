import json
import logging
from collections.abc import Awaitable, Callable

from app.errors.schemas import ErrorEventPayload, EventEnvelope
from app.errors.service import ErrorsService
from app.messaging.consumer import PermanentError

logger = logging.getLogger(__name__)


def parse_and_validate_message(raw: bytes) -> EventEnvelope[ErrorEventPayload]:
    """Parse raw Kafka bytes and validate against EventEnvelope and ErrorEventPayload.

    Raises PermanentError on bad messages (invalid JSON, legacy flat message, unsupported version,
    missing fields, validation failure, event_id mismatch).
    """
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise PermanentError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise PermanentError("Message payload must be a JSON object")

    # Reject legacy flat messages missing schema_version or payload nesting
    if "schema_version" not in data:
        raise PermanentError("Legacy flat message rejected: missing 'schema_version'")

    schema_version = data.get("schema_version")
    if schema_version != 1:
        raise PermanentError(f"Unsupported schema_version: {schema_version} (only version 1 is supported)")

    # Required envelope fields
    for field in ("event_id", "workspace_id", "project_id", "received_at", "payload"):
        if field not in data or data[field] is None:
            raise PermanentError(f"Missing required envelope field: {field}")

    if not isinstance(data.get("payload"), dict):
        raise PermanentError("Envelope 'payload' must be a JSON object")

    try:
        envelope = EventEnvelope[ErrorEventPayload].model_validate(data)
    except Exception as exc:
        raise PermanentError(f"Envelope validation failed: {exc}") from exc

    # Enforce envelope event_id matches payload event_id
    if str(envelope.event_id) != str(envelope.payload.event_id):
        raise PermanentError(
            f"Envelope event_id ({envelope.event_id}) does not match payload event_id ({envelope.payload.event_id})"
        )

    return envelope


def build_handler(
    service: ErrorsService,
) -> Callable[[bytes, str, int, int], Awaitable[None]]:
    """Build message handler for errors consumer."""

    async def handler(raw: bytes, topic: str, partition: int, offset: int) -> None:
        envelope = parse_and_validate_message(raw)
        result = await service.process_event(envelope)

        logger.info(
            "Event processed: event_id=%s project_id=%s issue_id=%s is_new=%s inserted=%s topic=%s partition=%d offset=%d",
            result.event_id,
            result.project_id,
            result.issue_id,
            result.is_new,
            result.inserted,
            topic,
            partition,
            offset,
        )

    return handler
