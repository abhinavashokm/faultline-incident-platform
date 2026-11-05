import re
from typing import Any

# Sensitive keys regex (case-insensitive)
SENSITIVE_KEY_PATTERN = re.compile(
    r"(auth|authorization|cookie|set-cookie|password|passwd|token|secret|api[_-]?key|card|cvv|ssn|private[_-]?key)",
    re.IGNORECASE,
)

# Credit card numbers pattern (13 to 19 digits with optional spaces or dashes)
CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

# Bearer token pattern in strings
BEARER_TOKEN_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.~+/]+=*", re.IGNORECASE)

MAX_REDACTION_DEPTH = 20


def redact_sensitive_data(
    obj: Any,
    key_name: str | None = None,
    depth: int = 0,
    seen: set[int] | None = None,
) -> Any:
    """Recursively scrub sensitive keys, authorization tokens, and payment card numbers.

    Guards against circular references and deep recursion.
    """
    if key_name and SENSITIVE_KEY_PATTERN.search(key_name):
        return "[REDACTED]"

    if depth > MAX_REDACTION_DEPTH:
        return "[MAX_DEPTH_REACHED]"

    if seen is None:
        seen = set()

    obj_id = id(obj)
    if isinstance(obj, (dict, list, tuple, set)):
        if obj_id in seen:
            return "[CIRCULAR]"
        seen.add(obj_id)

    try:
        if isinstance(obj, dict):
            return {
                str(k): redact_sensitive_data(v, key_name=str(k), depth=depth + 1, seen=seen)
                for k, v in obj.items()
            }
        elif isinstance(obj, (list, tuple)):
            res = [
                redact_sensitive_data(item, key_name=key_name, depth=depth + 1, seen=seen)
                for item in obj
            ]
            return tuple(res) if isinstance(obj, tuple) else res
        elif isinstance(obj, set):
            return [
                redact_sensitive_data(item, key_name=key_name, depth=depth + 1, seen=seen)
                for item in obj
            ]
        elif isinstance(obj, str):
            val = obj
            if CARD_NUMBER_PATTERN.search(val):
                val = CARD_NUMBER_PATTERN.sub("[REDACTED]", val)
            if BEARER_TOKEN_PATTERN.search(val):
                val = BEARER_TOKEN_PATTERN.sub(r"\1[REDACTED]", val)
            return val
        return obj
    finally:
        if isinstance(obj, (dict, list, tuple, set)):
            seen.discard(obj_id)


def redact_headers(headers: dict[str, Any]) -> dict[str, str]:
    """Scrub sensitive HTTP request headers (Authorization, Cookie, API keys)."""
    if not isinstance(headers, dict):
        return {}

    scrubbed: dict[str, str] = {}
    for key, value in headers.items():
        k_str = str(key)
        v_str = str(value)
        if SENSITIVE_KEY_PATTERN.search(k_str):
            scrubbed[k_str] = "[REDACTED]"
        else:
            if CARD_NUMBER_PATTERN.search(v_str):
                v_str = CARD_NUMBER_PATTERN.sub("[REDACTED]", v_str)
            if BEARER_TOKEN_PATTERN.search(v_str):
                v_str = BEARER_TOKEN_PATTERN.sub(r"\1[REDACTED]", v_str)
            scrubbed[k_str] = v_str
    return scrubbed

