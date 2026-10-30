from datetime import datetime, timezone
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.event import ErrorEventIngestRequest, redact_sensitive_data


def test_redact_sensitive_keys():
    raw_context = {
        "user_id": 42,
        "authorization": "Bearer secret-token-value",
        "nested": {
            "password": "my-plain-password",
            "api_key": "live_key_abcdef",
            "session_cookie": "sess_12345",
            "public_info": "safe_data",
        },
        "tags": ["prod", "auth-service"],
    }

    redacted = redact_sensitive_data(raw_context)

    assert redacted["user_id"] == 42
    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["api_key"] == "[REDACTED]"
    assert redacted["nested"]["session_cookie"] == "[REDACTED]"
    assert redacted["nested"]["public_info"] == "safe_data"
    assert redacted["tags"] == ["prod", "auth-service"]


def test_redact_credit_card_numbers():
    raw_context = {
        "message": "Payment failed for card 4111-2222-3333-4444 during checkout",
        "description": "Card 5500 0000 0000 0004 was declined",
    }
    redacted = redact_sensitive_data(raw_context)
    assert "[REDACTED]" in redacted["message"]
    assert "4111-2222-3333-4444" not in redacted["message"]
    assert "[REDACTED]" in redacted["description"]
    assert "5500 0000 0000 0004" not in redacted["description"]


def test_redaction_in_pydantic_schema():
    event = ErrorEventIngestRequest(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(timezone.utc),
        exception_type="PaymentError",
        context={
            "headers": {
                "Authorization": "Bearer supersecret",
                "Cookie": "uid=123; session=abc",
            },
            "user": {
                "email": "user@example.com",
                "api_secret": "my-secret",
            },
        },
    )
    assert event.context["headers"]["Authorization"] == "[REDACTED]"
    assert event.context["headers"]["Cookie"] == "[REDACTED]"
    assert event.context["user"]["api_secret"] == "[REDACTED]"
    assert event.context["user"]["email"] == "user@example.com"


def test_context_serialized_size_limit():
    large_context = {"data": "x" * (70 * 1024)}  # 70 KB > 64 KB limit
    with pytest.raises(ValidationError) as exc_info:
        ErrorEventIngestRequest(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            exception_type="ValueError",
            context=large_context,
        )
    assert "context exceeds maximum allowed size" in str(exc_info.value)

