import hashlib
import re
from collections.abc import Sequence

from app.errors.schemas import StackFrame

FINGERPRINT_VERSION = 1


def pick_frame(frames: Sequence[StackFrame | dict]) -> StackFrame | dict | None:
    candidates = [
        f
        for f in frames
        if (f.get("in_app") if isinstance(f, dict) else getattr(f, "in_app", False))
    ] or list(frames)
    return candidates[-1] if candidates else None


def make_fingerprint(
    exception_type: str,
    message: str,
    frames: Sequence[StackFrame | dict],
) -> tuple[str, str | None]:
    frame = pick_frame(frames)
    if frame is not None:
        file = frame.get("file") if isinstance(frame, dict) else frame.file
        function = frame.get("function") if isinstance(frame, dict) else frame.function
        location = f"{file}:{function}"
        culprit = f"{function} in {file}"[:255]
    else:
        location = re.sub(r"\d+", "N", message or "")
        culprit = None

    raw = f"v{FINGERPRINT_VERSION}|{exception_type}|{location}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest(), culprit

