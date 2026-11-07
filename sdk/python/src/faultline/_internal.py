import functools
import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger("faultline")

F = TypeVar("F", bound=Callable[..., Any])


def safe_call(func: F) -> F:
    """Decorator to wrap SDK functions so internal exceptions never crash the host application.

    Any caught exception is logged to the 'faultline' logger and the function returns None.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.error("Faultline SDK internal error in %s: %s", func.__name__, exc, exc_info=True)
            return None

    return wrapper  # type: ignore[return-value]


def truncate_string(value: str | None, max_length: int = 2000) -> str:
    """Safely truncate strings to prevent unbounded memory growth."""
    if value is None:
        return ""
    if len(value) > max_length:
        return value[:max_length]
    return value
