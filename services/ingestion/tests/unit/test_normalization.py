from datetime import datetime, timezone
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.event import ErrorEventIngestRequest, StackFrame


def test_message_truncation():
    raw_message = "A" * 3000
    event = ErrorEventIngestRequest(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(timezone.utc),
        exception_type="ValueError",
        message=raw_message,
    )
    assert len(event.message) == 2000
    assert event.message == "A" * 2000


def test_http_method_normalization():
    event = ErrorEventIngestRequest(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(timezone.utc),
        exception_type="ValueError",
        http_method=" get ",
    )
    assert event.http_method == "GET"

    with pytest.raises(ValidationError):
        ErrorEventIngestRequest(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            exception_type="ValueError",
            http_method="VERYLONGMETHODNAME",
        )


def test_environment_normalization():
    event = ErrorEventIngestRequest(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(timezone.utc),
        exception_type="ValueError",
        environment=" PRODUCTION-EU_01 ",
    )
    assert event.environment == "production-eu_01"

    # Invalid characters in environment
    with pytest.raises(ValidationError):
        ErrorEventIngestRequest(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            exception_type="ValueError",
            environment="production.staging@eu",
        )


def test_status_code_smallint_validation():
    # Valid smallints
    event = ErrorEventIngestRequest(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(timezone.utc),
        exception_type="ValueError",
        status_code=500,
    )
    assert event.status_code == 500

    # Invalid smallint (> 32767)
    with pytest.raises(ValidationError):
        ErrorEventIngestRequest(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            exception_type="ValueError",
            status_code=65535,
        )


def test_stack_frames_cap():
    frames = [
        StackFrame(file=f"file_{i}.py", function="run", line=i, in_app=True)
        for i in range(150)
    ]
    event = ErrorEventIngestRequest(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(timezone.utc),
        exception_type="ValueError",
        stack_frames=frames,
    )
    # Default cap is 100; innermost frames should be kept
    assert len(event.stack_frames) == 100
    assert event.stack_frames[0].line == 50
    assert event.stack_frames[-1].line == 149


def test_user_hash_and_lengths():
    valid_hash = "a" * 64
    event = ErrorEventIngestRequest(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(timezone.utc),
        exception_type="ValueError",
        user_hash=valid_hash,
    )
    assert event.user_hash == valid_hash

    with pytest.raises(ValidationError):
        ErrorEventIngestRequest(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            exception_type="ValueError",
            user_hash="a" * 65,
        )

