import sys
import threading
from types import TracebackType
from typing import Any, Callable

from faultline._internal import logger

_orig_sys_excepthook: Callable[[type[BaseException], BaseException, TracebackType | None], Any] | None = None
_orig_threading_excepthook: Callable[[Any], Any] | None = None
_installed: bool = False
_lock = threading.Lock()


def install_excepthooks() -> None:
    """Install global sys.excepthook and threading.excepthook handlers that chain to previous hooks."""
    global _orig_sys_excepthook, _orig_threading_excepthook, _installed

    with _lock:
        if _installed:
            return

        _orig_sys_excepthook = sys.excepthook
        _orig_threading_excepthook = getattr(threading, "excepthook", None)

        def _faultline_sys_excepthook(
            exc_type: type[BaseException],
            exc_value: BaseException,
            exc_traceback: TracebackType | None,
        ) -> None:
            try:
                # Import lazily to avoid circular imports
                from faultline.client import get_client
                client = get_client()
                if client is not None and exc_value is not None:
                    client.capture_exception(exc_value, level="fatal")
            except Exception as err:
                logger.error("Failed to capture exception in sys.excepthook: %s", err)
            finally:
                if _orig_sys_excepthook is not None:
                    _orig_sys_excepthook(exc_type, exc_value, exc_traceback)

        def _faultline_threading_excepthook(args: Any) -> None:
            try:
                from faultline.client import get_client
                client = get_client()
                if client is not None and getattr(args, "exc_value", None) is not None:
                    client.capture_exception(args.exc_value, level="fatal")
            except Exception as err:
                logger.error("Failed to capture exception in threading.excepthook: %s", err)
            finally:
                if _orig_threading_excepthook is not None:
                    _orig_threading_excepthook(args)

        sys.excepthook = _faultline_sys_excepthook
        if hasattr(threading, "excepthook"):
            threading.excepthook = _faultline_threading_excepthook

        _installed = True


def uninstall_excepthooks() -> None:
    """Restore the original excepthook handlers."""
    global _orig_sys_excepthook, _orig_threading_excepthook, _installed

    with _lock:
        if not _installed:
            return

        if _orig_sys_excepthook is not None:
            sys.excepthook = _orig_sys_excepthook
            _orig_sys_excepthook = None

        if hasattr(threading, "excepthook") and _orig_threading_excepthook is not None:
            threading.excepthook = _orig_threading_excepthook
            _orig_threading_excepthook = None

        _installed = False

