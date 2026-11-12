import threading
from typing import Any

from faultline._internal import logger, safe_call
from faultline.config import Config
from faultline.event import build_error_event, build_message_event
from faultline.redaction import redact_sensitive_data
from faultline.transport import Transport

_GLOBAL_CLIENT: "Client | None" = None
_CLIENT_LOCK = threading.Lock()


class Client:
    """Core Faultline client responsible for telemetry capture and lifecycle management."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.transport = Transport(config)

    def capture_exception(
        self,
        exc: BaseException,
        *,
        level: str = "error",
        route_template: str | None = None,
        http_method: str | None = None,
        status_code: int | None = None,
        service: str | None = None,
        user_hash: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str | None:
        """Capture an exception, scrub sensitive data, and enqueue for background delivery.

        Returns:
            The event ID if the event was accepted into the queue, otherwise None.

            Note: a returned ID means the event was *queued*, not *delivered*.
            Delivery happens asynchronously in a background thread and may still
            fail (network errors, invalid key, retries exhausted) without
            notifying the caller. None means the event was dropped, either
            because the queue is full, the client is closed, or an error
            occurred while building the event.
        """
        try:
            # Redact context prior to serialization
            scrubbed_context = redact_sensitive_data(context) if context else {}

            event = build_error_event(
                exc,
                release=self.config.release,
                environment=self.config.environment,
                service=service or self.config.service,
                route_template=route_template,
                http_method=http_method,
                status_code=status_code,
                user_hash=user_hash,
                context=scrubbed_context,
                level=level,  # type: ignore[arg-type]
            )

            # Scrub any other sensitive keys in top-level event if present
            event["context"] = scrubbed_context

            enqueued = self.transport.send(event)
            if enqueued:
                return event["event_id"]
            return None
        except Exception as err:
            logger.error("Failed to capture exception: %s", err, exc_info=True)
            return None

    def capture_message(
        self,
        message: str,
        *,
        level: str = "warning",
        route_template: str | None = None,
        http_method: str | None = None,
        status_code: int | None = None,
        service: str | None = None,
        user_hash: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str | None:
        """Capture a custom log or event message and enqueue for background delivery."""
        try:
            scrubbed_context = redact_sensitive_data(context) if context else {}

            event = build_message_event(
                message,
                release=self.config.release,
                environment=self.config.environment,
                service=service or self.config.service,
                route_template=route_template,
                http_method=http_method,
                status_code=status_code,
                user_hash=user_hash,
                context=scrubbed_context,
                level=level,  # type: ignore[arg-type]
            )

            enqueued = self.transport.send(event)
            if enqueued:
                return event["event_id"]
            return None
        except Exception as err:
            logger.error("Failed to capture message: %s", err, exc_info=True)
            return None

    def flush(self, timeout: float | None = None) -> bool:
        """Block until queued events are transmitted or timeout expires."""
        try:
            from faultline.performance import flush_performance_batch

            flush_performance_batch(client=self)
            return self.transport.flush(timeout=timeout)
        except Exception as err:
            logger.error("Failed to flush transport: %s", err, exc_info=True)
            return False

    def close(self, timeout: float | None = None) -> None:
        """Flush remaining events and terminate transport thread."""
        try:
            from faultline.performance import close_performance_batcher

            close_performance_batcher(client=self)
            self.transport.close(timeout=timeout)
        except Exception as err:
            logger.error("Failed to close client: %s", err, exc_info=True)


def get_client() -> Client | None:
    """Get the currently configured global client."""
    global _GLOBAL_CLIENT
    return _GLOBAL_CLIENT


def set_client(client: Client | None) -> None:
    """Set or replace the global client."""
    global _GLOBAL_CLIENT
    with _CLIENT_LOCK:
        if _GLOBAL_CLIENT is not None and _GLOBAL_CLIENT is not client:
            try:
                _GLOBAL_CLIENT.close()
            except Exception:
                pass
        _GLOBAL_CLIENT = client
