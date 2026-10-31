import hashlib
import re
from collections.abc import Sequence
from typing import Any

from app.errors.schemas import StackFrame

FINGERPRINT_VERSION = 1

UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
QUOTED_STR_PATTERN = re.compile(r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\")")
HEX_PATTERN = re.compile(r"\b(?:0x)?[0-9a-fA-F]{8,}\b")
NUM_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_message(msg: str | None) -> str:
    """Normalize exception message by replacing dynamic tokens and collapsing whitespace.

    Replaces:
    1. UUIDs -> <UUID>
    2. Quoted strings -> <STR>
    3. Hex strings (8+ chars) -> <HEX>
    4. Numbers -> <NUM>
    5. Collapses whitespace
    """
    if not msg:
        return ""

    text = msg
    text = UUID_PATTERN.sub("<UUID>", text)
    text = QUOTED_STR_PATTERN.sub("<STR>", text)
    text = HEX_PATTERN.sub("<HEX>", text)
    text = NUM_PATTERN.sub("<NUM>", text)
    text = WHITESPACE_PATTERN.sub(" ", text).strip()
    return text


def compute_fingerprint(
    exception_type: str,
    stack_frames: Sequence[StackFrame | dict[str, Any]] | None = None,
    route_template: str | None = None,
    message: str | None = None,
) -> str:
    """Compute a deterministic SHA-256 fingerprint (version 1).

    Signature selection:
    1. Primary: exception_type + up to 3 in_app frames as 'file:function' (last 3, innermost call sites).
       Line numbers are NEVER used.
    2. Fallback 1: exception_type + normalized route_template if present and no in_app frames.
    3. Fallback 2: exception_type + normalized message (tokens scrubbed) if no in_app frames and no route.
    """
    frames = stack_frames or []
    in_app_frames: list[tuple[str, str]] = []

    for f in frames:
        is_in_app = f.in_app if hasattr(f, "in_app") else f.get("in_app", False)
        if is_in_app:
            file_name = f.file if hasattr(f, "file") else str(f.get("file", ""))
            func_name = f.function if hasattr(f, "function") else str(f.get("function", ""))
            in_app_frames.append((file_name, func_name))

    if in_app_frames:
        # Assumption: frames arrive in standard Python traceback order (oldest first).
        # We take the last 3 in-app frames (closest to the actual failure site).
        selected_frames = in_app_frames[-3:]
        frame_parts = [f"{file}:{func}" for file, func in selected_frames]
        canonical = f"v{FINGERPRINT_VERSION}|" + "|".join([exception_type] + frame_parts)
    elif route_template and route_template.strip():
        norm_route = route_template.strip()
        canonical = f"v{FINGERPRINT_VERSION}|{exception_type}|{norm_route}"
    else:
        norm_msg = normalize_message(message)
        canonical = f"v{FINGERPRINT_VERSION}|{exception_type}|{norm_msg}"

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_title(exception_type: str, message: str | None) -> str:
    """Derive issue title: exception_type plus first line of message, truncated to 500 characters."""
    msg = message or ""
    lines = msg.splitlines()
    first_line = lines[0].strip() if lines else ""
    if first_line:
        full_title = f"{exception_type}: {first_line}"
    else:
        full_title = exception_type
    return full_title[:500]


def derive_culprit(
    stack_frames: Sequence[StackFrame | dict[str, Any]] | None,
    route_template: str | None,
) -> str | None:
    """Derive issue culprit: top in_app frame 'file:function' (innermost frame), else route_template, else None."""
    frames = stack_frames or []
    in_app_frames: list[tuple[str, str]] = []

    for f in frames:
        is_in_app = f.in_app if hasattr(f, "in_app") else f.get("in_app", False)
        if is_in_app:
            file_name = f.file if hasattr(f, "file") else str(f.get("file", ""))
            func_name = f.function if hasattr(f, "function") else str(f.get("function", ""))
            in_app_frames.append((file_name, func_name))

    if in_app_frames:
        # Innermost in_app frame
        file, func = in_app_frames[-1]
        return f"{file}:{func}"[:255]

    if route_template and route_template.strip():
        return route_template.strip()[:255]

    return None
