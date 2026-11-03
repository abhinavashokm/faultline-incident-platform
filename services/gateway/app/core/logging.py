import contextvars
import logging

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class StructuredLogFormatter(logging.Formatter):
    """Formats log records with request_id contextual info."""

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
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

