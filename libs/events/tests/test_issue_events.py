import json
import uuid
from datetime import datetime, timezone

from pydantic import TypeAdapter

from faultline_events import (
    IssueCreatedEvent,
    IssueCreatedPayload,
    IssueEvent,
    TOPIC_ISSUE_EVENTS,
)


def test_issue_created_event_serialization_and_validation():
    event_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    issue_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    payload = IssueCreatedPayload(
        issue_id=issue_id,
        title="ValueError: invalid literal for int()",
        level="error",
        environment="production",
        release="v1.2.3",
        first_seen=now,
    )

    event = IssueCreatedEvent(
        event_id=event_id,
        schema_version=1,
        occurred_at=now,
        workspace_id=workspace_id,
        project_id=project_id,
        payload=payload,
    )

    assert event.event_type == "issue.created"
    assert event.payload.issue_id == issue_id
    assert TOPIC_ISSUE_EVENTS == "issue-events"

    # Test JSON serialization and deserialization via discriminated union
    raw_json = event.model_dump_json()
    adapter = TypeAdapter(IssueEvent)
    parsed = adapter.validate_json(raw_json)

    assert isinstance(parsed, IssueCreatedEvent)
    assert parsed.event_id == event_id
    assert parsed.payload.title == "ValueError: invalid literal for int()"
