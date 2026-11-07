from datetime import datetime
import uuid
import pytest

from faultline.event import build_error_event, build_message_event, normalize_environment
from faultline.stacktrace import extract_stack_frames, is_in_app


def test_is_in_app():
    assert is_in_app("/home/user/app/main.py") is True
    assert is_in_app("/home/user/.venv/lib/python3.12/site-packages/fastapi/main.py") is False
    assert is_in_app("<frozen importlib._bootstrap>") is False
    assert is_in_app("/faultline/event.py") is False


def test_extract_stack_frames():
    def inner():
        raise ValueError("inner failure")

    def outer():
        inner()

    try:
        outer()
    except ValueError as exc:
        frames = extract_stack_frames(exc)

    assert len(frames) >= 2
    assert frames[-1]["function"] == "inner"
    assert "test_event.py" in frames[-1]["file"]
    assert frames[-1]["line"] is not None
    assert frames[-1]["in_app"] is True


def test_build_error_event():
    try:
        raise RuntimeError("Something went wrong")
    except RuntimeError as exc:
        event = build_error_event(
            exc,
            release="v1.2.3",
            environment="Production",
            service="order-service",
            route_template="/orders/{id}",
            http_method="get",
            status_code=500,
        )

    # Validate UUID
    uuid.UUID(event["event_id"])
    # Validate timestamp
    datetime.fromisoformat(event["occurred_at"])

    assert event["exception_type"] == "RuntimeError"
    assert event["message"] == "Something went wrong"
    assert event["event_type"] == "error"
    assert event["level"] == "error"
    assert event["release"] == "v1.2.3"
    assert event["environment"] == "production"
    assert event["service"] == "order-service"
    assert event["route_template"] == "/orders/{id}"
    assert event["http_method"] == "GET"
    assert event["status_code"] == 500
    assert "project_id" not in event
    assert "workspace_id" not in event
    assert isinstance(event["stack_frames"], list)
    assert len(event["stack_frames"]) > 0


def test_build_message_event():
    event = build_message_event(
        "User reached rate limit threshold",
        level="warning",
        release="v1.0.0",
        environment="staging",
    )

    uuid.UUID(event["event_id"])
    assert event["event_type"] == "message"
    assert event["level"] == "warning"
    assert event["message"] == "User reached rate limit threshold"
    assert event["exception_type"] == "Message"
    assert event["environment"] == "staging"


def test_event_string_truncation():
    huge_msg = "x" * 5000
    try:
        raise ValueError(huge_msg)
    except ValueError as exc:
        event = build_error_event(exc)

    assert len(event["message"]) == 2000


def test_normalize_environment():
    assert normalize_environment("Production_US-East") == "production_us-east"
    assert normalize_environment("prod.server#1") == "prod-server-1"
    assert normalize_environment("") is None

