from datetime import datetime, timezone
import json
import uuid
from faultline_events import EventEnvelope

from app.schemas.event import ErrorEventIngestRequest, NormalizedErrorEvent


def test_event_envelope_creation_and_serialization():
    event_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    received_at = datetime.now(timezone.utc)
    occurred_at = datetime.now(timezone.utc)

    normalized_payload = NormalizedErrorEvent(
        event_id=event_id,
        occurred_at=occurred_at,
        exception_type="KeyError",
        message="Missing user_id",
        event_type="error",
        level="error",
        service="order-service",
        environment="production",
        context={"user": "alice"},
    )

    envelope = EventEnvelope[NormalizedErrorEvent](
        schema_version=1,
        event_id=event_id,
        workspace_id=workspace_id,
        project_id=project_id,
        received_at=received_at,
        payload=normalized_payload,
    )

    assert envelope.schema_version == 1
    assert envelope.event_id == event_id
    assert envelope.workspace_id == workspace_id
    assert envelope.project_id == project_id
    assert envelope.received_at == received_at
    assert envelope.payload.exception_type == "KeyError"

    serialized = envelope.model_dump_json()
    data = json.loads(serialized)

    assert data["schema_version"] == 1
    assert data["event_id"] == str(event_id)
    assert data["workspace_id"] == str(workspace_id)
    assert data["project_id"] == str(project_id)
    assert data["payload"]["service"] == "order-service"

