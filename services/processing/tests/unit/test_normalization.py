from app.errors.fingerprint import derive_title
from app.errors.service import (
    cap_context,
    normalize_event_type,
    normalize_level,
    scrub_message,
)


def test_level_mapping():
    assert normalize_level("error") == "error"
    assert normalize_level("ERROR") == "error"
    assert normalize_level("warning") == "warning"
    assert normalize_level("warn") == "warning"
    assert normalize_level("fatal") == "fatal"
    assert normalize_level("critical") == "fatal"
    assert normalize_level("panic") == "fatal"
    # Unknown values map to error
    assert normalize_level("info") == "error"
    assert normalize_level("debug") == "error"
    assert normalize_level(None) == "error"
    assert normalize_level("") == "error"


def test_event_type_mapping():
    assert normalize_event_type("error") == "error"
    assert normalize_event_type("message") == "message"
    assert normalize_event_type("ERROR") == "error"
    assert normalize_event_type("unknown") == "error"
    assert normalize_event_type(None) == "error"


def test_message_scrubbing_and_truncation():
    # Scrub control characters while keeping standard whitespace \n, \t
    raw = "Error occurred\x00\x07 in module\t\n\x1b[31mred\x1b[0m"
    scrubbed = scrub_message(raw)
    assert "\x00" not in scrubbed
    assert "\x07" not in scrubbed
    assert "\x1b" not in scrubbed
    assert "\t" in scrubbed
    assert "\n" in scrubbed

    # Truncate to 2000 characters
    huge = "a" * 2500
    truncated = scrub_message(huge)
    assert len(truncated) == 2000


def test_title_truncation():
    long_msg = "A" * 600
    title = derive_title("IndexError", long_msg)
    assert len(title) == 500
    assert title.startswith("IndexError: AAA")


def test_context_byte_cap():
    small_context = {"user_id": 123, "role": "admin"}
    assert cap_context(small_context, max_bytes=1024) == small_context

    # Exceeding byte cap truncates with marker
    large_context = {"data": "x" * 20000}
    capped = cap_context(large_context, max_bytes=16384)
    assert capped == {"_truncated": True}

    # Non-serializable context also falls back safely
    class BadObj:
        pass

    assert cap_context({"bad": BadObj()}, max_bytes=1024) == {"_truncated": True}

