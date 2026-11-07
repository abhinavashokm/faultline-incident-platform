"""Faultline Python SDK for error tracking and incident response."""

from typing import Any

from faultline._internal import logger, safe_call
from faultline.client import Client, get_client, set_client
from faultline.config import Config
from faultline.dsn import Dsn, DsnError, parse_dsn
from faultline.integrations.excepthook import install_excepthooks

__version__ = "0.1.0"
__all__ = [
    "init",
    "capture_exception",
    "capture_message",
    "flush",
    "close",
    "get_client",
    "Client",
    "Config",
    "Dsn",
    "DsnError",
]


def init(
    dsn: str,
    *,
    release: str | None = None,
    environment: str = "production",
    service: str | None = None,
    install_sys_excepthook: bool = True,
    **kwargs: Any,
) -> Client:
    """Initialize the Faultline SDK.

    Validates the DSN and raises DsnError if it is malformed.
    Other parameters (such as release, environment, service) are configured.
    If release is not provided, the APP_RELEASE environment variable is used.
    """
    # Note: parse_dsn will raise DsnError directly on malformed DSN, as required.
    config = Config.from_options(
        dsn=dsn,
        release=release,
        environment=environment,
        service=service,
        **kwargs,
    )

    client = Client(config)
    set_client(client)

    if install_sys_excepthook:
        try:
            install_excepthooks()
        except Exception as exc:
            logger.error("Failed to install excepthooks: %s", exc)

    return client


@safe_call
def capture_exception(exc: BaseException, **kwargs: Any) -> str | None:
    """Capture an exception and send it to Faultline.

    Safe entry point: will never crash the host application.
    """
    client = get_client()
    if client is None:
        logger.debug("Faultline SDK is not initialized; capture_exception ignored.")
        return None
    return client.capture_exception(exc, **kwargs)


@safe_call
def capture_message(message: str, **kwargs: Any) -> str | None:
    """Capture a custom log or event message and send it to Faultline.

    Safe entry point: will never crash the host application.
    """
    client = get_client()
    if client is None:
        logger.debug("Faultline SDK is not initialized; capture_message ignored.")
        return None
    return client.capture_message(message, **kwargs)


@safe_call
def flush(timeout: float = 2.0) -> bool:
    """Flush pending events to Faultline within timeout seconds."""
    client = get_client()
    if client is None:
        return True
    return client.flush(timeout=timeout)


@safe_call
def close(timeout: float = 2.0) -> None:
    """Flush pending events and shut down the Faultline SDK."""
    client = get_client()
    if client is not None:
        client.close(timeout=timeout)
        set_client(None)

