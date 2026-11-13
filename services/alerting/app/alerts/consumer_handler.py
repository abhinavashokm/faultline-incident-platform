import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import ValidationError

from faultline_events import IssueCreatedEvent
from app.alerts.evaluation_service import AlertEvaluationService
from app.messaging.consumer import PermanentError

logger = logging.getLogger(__name__)

HandlerFunc = Callable[[dict[str, Any], AlertEvaluationService], Awaitable[None]]


async def handle_issue_created_event(
    data: dict[str, Any],
    service: AlertEvaluationService,
) -> None:
    try:
        event = IssueCreatedEvent.model_validate(data)
    except ValidationError as exc:
        raise PermanentError(f"Malformed issue.created event: {exc}") from exc

    await service.handle_issue_created(event)


class EventHandlerRegistry:
    """Registry mapping event_type to async handler functions."""

    def __init__(self) -> None:
        self._handlers: dict[str, HandlerFunc] = {}

    def register(self, event_type: str, handler: HandlerFunc) -> None:
        self._handlers[event_type] = handler

    def get(self, event_type: str) -> HandlerFunc | None:
        return self._handlers.get(event_type)


registry = EventHandlerRegistry()
registry.register("issue.created", handle_issue_created_event)


def build_alerts_consumer_handler(
    service: AlertEvaluationService,
) -> Callable[[bytes, str, int, int], Awaitable[None]]:
    """Build Kafka message handler for alerts consumer."""

    async def handler(raw: bytes, topic: str, partition: int, offset: int) -> None:
        try:
            data = json.loads(raw)
        except Exception as exc:
            raise PermanentError(f"Invalid JSON message: {exc}") from exc

        if not isinstance(data, dict):
            raise PermanentError("Event message must be a JSON object")

        event_type = data.get("event_type")
        if not event_type or not isinstance(event_type, str):
            raise PermanentError("Message missing valid 'event_type'")

        handler_func = registry.get(event_type)
        if handler_func is None:
            logger.warning(
                "Unknown event_type %r received on topic=%s partition=%d offset=%d; skipping",
                event_type,
                topic,
                partition,
                offset,
            )
            return

        await handler_func(data, service)

    return handler
