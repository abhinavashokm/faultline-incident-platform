import json
import uuid
from datetime import datetime, timezone

import pytest

from app.errors.consumer import parse_and_validate_message
from app.messaging.consumer import PermanentError


def test_valid_message_passes():
    event_id = str(uuid.uuid4())
    payload = {
        "schema_version": 1,
        "event_id": event_id,
        "workspace_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "event_id": event_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "exception_type": "ValueError",
            "message": "test error",
            "stack_frames": [
                {"file": "app.py", "function": "foo", "line": 10, "in_app": True}
            ],
            "event_type": "error",
            "level": "error",
            "context": {"key": "val"},
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    envelope = parse_and_validate_message(raw)
    assert envelope.schema_version == 1
    assert str(envelope.event_id) == event_id
    assert envelope.payload.exception_type == "ValueError"


def test_legacy_flat_message_raises_permanent_error():
    # Legacy flat message without schema_version or payload nesting
    legacy = {
        "event_id": str(uuid.uuid4()),
        "workspace_id": "11111111-1111-1111-1111-111111111111",
        "project_id": "22222222-2222-2222-2222-222222222222",
        "exception_type": "LegacyError",
        "message": "flat message without envelope",
    }
    raw = json.dumps(legacy).encode("utf-8")
    with pytest.raises(PermanentError) as exc_info:
        parse_and_validate_message(raw)
    assert "schema_version" in str(exc_info.value)


def test_unsupported_schema_version_raises_permanent_error():
    event_id = str(uuid.uuid4())
    payload = {
        "schema_version": 2,
        "event_id": event_id,
        "workspace_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "event_id": event_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "exception_type": "ValueError",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    with pytest.raises(PermanentError) as exc_info:
        parse_and_validate_message(raw)
    assert "Unsupported schema_version: 2" in str(exc_info.value)


def test_envelope_event_id_mismatch_raises_permanent_error():
    env_event_id = str(uuid.uuid4())
    payload_event_id = str(uuid.uuid4())
    payload = {
        "schema_version": 1,
        "event_id": env_event_id,
        "workspace_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "event_id": payload_event_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "exception_type": "ValueError",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    with pytest.raises(PermanentError) as exc_info:
        parse_and_validate_message(raw)
    assert "does not match" in str(exc_info.value)


def test_invalid_json_raises_permanent_error():
    raw = b"this is not valid json {"
    with pytest.raises(PermanentError) as exc_info:
        parse_and_validate_message(raw)
    assert "Invalid JSON" in str(exc_info.value)


def test_missing_required_fields_raises_permanent_error():
    # Missing project_id
    payload = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "workspace_id": str(uuid.uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "event_id": str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "exception_type": "ValueError",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    with pytest.raises(PermanentError) as exc_info:
        parse_and_validate_message(raw)
    assert "Missing required envelope field" in str(exc_info.value)

