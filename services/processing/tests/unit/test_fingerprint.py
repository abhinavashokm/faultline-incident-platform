import re

from app.errors.fingerprint import (
    compute_fingerprint,
    derive_culprit,
    derive_title,
    normalize_message,
)
from app.errors.schemas import StackFrame


def test_fingerprint_same_error_different_line_numbers():
    frames1 = [
        StackFrame(file="app/api.py", function="handle_request", line=42, in_app=True),
        StackFrame(file="app/service.py", function="do_work", line=105, in_app=True),
    ]
    frames2 = [
        StackFrame(file="app/api.py", function="handle_request", line=88, in_app=True),
        StackFrame(file="app/service.py", function="do_work", line=210, in_app=True),
    ]

    fp1 = compute_fingerprint("ValueError", frames1, message="Invalid value")
    fp2 = compute_fingerprint("ValueError", frames2, message="Invalid value")

    assert fp1 == fp2
    assert len(fp1) == 64


def test_fingerprint_different_in_app_function():
    frames1 = [
        StackFrame(file="app/service.py", function="func_a", line=10, in_app=True),
    ]
    frames2 = [
        StackFrame(file="app/service.py", function="func_b", line=10, in_app=True),
    ]

    fp1 = compute_fingerprint("RuntimeError", frames1)
    fp2 = compute_fingerprint("RuntimeError", frames2)

    assert fp1 != fp2


def test_fingerprint_different_message_values_same_frames():
    frames = [
        StackFrame(file="app/auth.py", function="authenticate", line=15, in_app=True),
    ]

    # Primary signature ignores raw message when in-app frames are present
    fp1 = compute_fingerprint("AuthError", frames, message="User 12345 failed")
    fp2 = compute_fingerprint("AuthError", frames, message="User 99999 failed")

    assert fp1 == fp2


def test_fingerprint_fallback_route_template_when_no_in_app():
    # Only non-in-app frames
    frames = [
        StackFrame(file="urllib3/connectionpool.py", function="urlopen", line=300, in_app=False),
    ]

    fp1 = compute_fingerprint(
        "HTTPError",
        frames,
        route_template="/api/v1/orders/{id}",
        message="Request timed out for order 123",
    )
    fp2 = compute_fingerprint(
        "HTTPError",
        frames,
        route_template="/api/v1/orders/{id}",
        message="Request timed out for order 456",
    )
    fp_different_route = compute_fingerprint(
        "HTTPError",
        frames,
        route_template="/api/v1/users/{id}",
        message="Request timed out for user 123",
    )

    assert fp1 == fp2
    assert fp1 != fp_different_route


def test_fingerprint_last_fallback_normalized_message():
    # No in-app frames and no route_template
    fp1 = compute_fingerprint(
        "DBConnectionError",
        stack_frames=[],
        route_template=None,
        message="Connection failed for user 550e8400-e29b-41d4-a716-446655440000 on port 5432 with 0xdeadbeef",
    )
    fp2 = compute_fingerprint(
        "DBConnectionError",
        stack_frames=[],
        route_template=None,
        message="Connection failed for user 123e4567-e89b-12d3-a456-426614174000 on port 9999 with 0x12345678",
    )

    assert fp1 == fp2
    assert len(fp1) == 64


def test_fingerprint_output_format_and_determinism():
    fp = compute_fingerprint("TypeError", message="cannot unpack None")
    assert re.match(r"^[0-9a-f]{64}$", fp)

    # Determinism: repeating with exact same inputs yields identical hash
    fp_repeat = compute_fingerprint("TypeError", message="cannot unpack None")
    assert fp == fp_repeat


def test_normalize_message_tokens():
    msg = (
        "Failed query for user 550e8400-e29b-41d4-a716-446655440000 "
        "with token 'secret_token_123' at 0xdeadbeef1234 and count 42.50\n   spaces"
    )
    normalized = normalize_message(msg)
    assert "<UUID>" in normalized
    assert "<STR>" in normalized
    assert "<HEX>" in normalized
    assert "<NUM>" in normalized
    assert "\n" not in normalized


def test_derive_title():
    # Multiline message
    title = derive_title("KeyError", "missing key: 'user_id'\nTraceback (most recent call last):")
    assert title == "KeyError: missing key: 'user_id'"

    # Truncation
    long_msg = "x" * 600
    title_long = derive_title("CustomError", long_msg)
    assert len(title_long) == 500


def test_derive_culprit():
    frames = [
        StackFrame(file="main.py", function="main", in_app=True),
        StackFrame(file="fastapi/routing.py", function="run_endpoint", in_app=False),
        StackFrame(file="app/billing.py", function="charge", in_app=True),
    ]
    culprit = derive_culprit(frames, "/api/checkout")
    assert culprit == "app/billing.py:charge"

    # Fallback to route
    culprit_fallback = derive_culprit([], "/api/checkout")
    assert culprit_fallback == "/api/checkout"

    # No frames, no route
    assert derive_culprit([], None) is None

