import logging
from collections.abc import Awaitable, Callable

from pydantic import ValidationError

from app.errors.schemas import ErrorEventPayload
from app.errors.service import ErrorsService
from app.messaging.consumer import PermanentError

logger = logging.getLogger(__name__)


def build_handler(service: ErrorsService) -> Callable[[bytes], Awaitable[None]]:
    async def handler(raw: bytes) -> None:
        try:
            event = ErrorEventPayload.model_validate_json(raw)
        except ValidationError as exc:
            raise PermanentError(f"Invalid error event payload: {exc}") from exc

        result = await service.process_event(event)
        logger.info("Processed event %s: %s", event.event_id, result)

    return handler

