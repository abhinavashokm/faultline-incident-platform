import contextvars
import json
import logging
from typing import Any

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def mask_key(key: str | None) -> str:
    """Mask a public key or secret, returning at most a short prefix."""
    if not key:
        return "<none>"
    if len(key) <= 6:
        return key[:2] + "..."
    return key[:6] + "..."


class StructuredLogFormatter(logging.Formatter):
    """Formats log records as structured text or JSON including request_id."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_var.get("-")
        record.request_id = req_id  # type: ignore[attr-defined]
        return super().format(record)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    formatter = StructuredLogFormatter(
        fmt="%(asctime)s [%(levelname)s] [req_id=%(request_id)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(handler)


def log_event_accepted(
    logger: logging.Logger,
    event_id: str,
    project_id: str,
    workspace_id: str,
) -> None:
    logger.info(
        "Event accepted: event_id=%s project_id=%s workspace_id=%s",
        event_id,
        project_id,
        workspace_id,
    )


def log_event_rejected(
    logger: logging.Logger,
    reason: str,
    status_code: int,
    key_prefix: str = "<none>",
    details: str = "",
) -> None:
    logger.warning(
        "Event rejected: reason=%s status=%d key=%s details=%s",
        reason,
        status_code,
        key_prefix,
        details,
    )


def log_kafka_failure(
    logger: logging.Logger,
    event_id: str,
    project_id: str,
    error: Exception,
) -> None:
    logger.error(
        "Kafka publish failed: event_id=%s project_id=%s error=%s",
        event_id,
        project_id,
        repr(error),
    )

