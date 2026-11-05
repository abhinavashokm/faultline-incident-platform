import sys
import sysconfig
import traceback
from types import TracebackType
from typing import Any

# Standard library paths to identify non-in-app frames
_STDLIB_PATHS: tuple[str, ...] = tuple(
    p for p in {
        sysconfig.get_path("stdlib"),
        sysconfig.get_path("platstdlib"),
    } if p
)


def is_in_app(filename: str) -> bool:
    """Determine if a filename belongs to application code rather than stdlib or dependencies."""
    if not filename or filename.startswith("<"):
        return False

    # Check for virtualenv or global site-packages
    if "site-packages" in filename or "dist-packages" in filename:
        return False

    # Check for SDK internal code
    if "/faultline/" in filename or filename.endswith("/faultline"):
        return False

    # Check for Python standard library
    for stdlib_path in _STDLIB_PATHS:
        if filename.startswith(stdlib_path):
            return False

    return True


def extract_stack_frames(
    tb_or_exc: BaseException | TracebackType | None = None,
    max_frames: int = 100,
) -> list[dict[str, Any]]:
    """Extract a list of normalized stack frame dictionaries from a traceback or exception.

    Caps frames at max_frames (keeping the innermost/most recent calls).
    Each frame contains:
      - file: str (max 1000)
      - function: str (max 255)
      - line: int | None
      - in_app: bool
    """
    tb: TracebackType | None = None
    if isinstance(tb_or_exc, BaseException):
        tb = tb_or_exc.__traceback__
    elif isinstance(tb_or_exc, TracebackType):
        tb = tb_or_exc

    if tb is not None:
        raw_frames = traceback.extract_tb(tb)
    else:
        # Fallback to current stack if no traceback provided
        raw_frames = traceback.extract_stack()[:-1]

    frames: list[dict[str, Any]] = []
    for frame in raw_frames:
        filename = frame.filename or ""
        function = frame.name or ""
        line = frame.lineno

        frames.append({
            "file": filename[-1000:],
            "function": function[:255],
            "line": line if (line is not None and line >= 0) else None,
            "in_app": is_in_app(filename),
        })

    if len(frames) > max_frames:
        # Keep innermost frames (call site)
        frames = frames[-max_frames:]

    return frames

