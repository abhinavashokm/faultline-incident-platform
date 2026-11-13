import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from faultline_events import IssueCreatedEvent
from app.errors.schemas import ErrorEventPayload, EventEnvelope, StackFrame
from app.errors.service import ErrorsService


class FakeIssueEventPublisher:
    def __init__(self, should_fail: bool = False) -> None:
        self.published: list[IssueCreatedEvent] = []
        self.should_fail = should_fail

    async def publish_issue_created(self, event: IssueCreatedEvent) -> None:
        if self.should_fail:
            raise RuntimeError("Kafka connection failed")
        self.published.append(event)


class FakeSession:
    def __init__(self, is_new: bool = True) -> None:
        self.is_new = is_new
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def begin(self):
        session = self

        class TransactionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    session.rolled_back = True
                else:
                    session.committed = True

        return TransactionContext()


@pytest.fixture
def sample_envelope() -> EventEnvelope[ErrorEventPayload]:
    event_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    now = datetime.now(timezone.utc)
    payload = ErrorEventPayload(
        event_id=event_id,
        occurred_at=now,
        exception_type="ValueError",
        message="Invalid literal for int()",
        event_type="error",
        level="error",
        environment="production",
        release="v1.0.0",
        stack_frames=[StackFrame(file="app/main.py", function="index", line=42, in_app=True)],
    )
    return EventEnvelope[ErrorEventPayload](
        schema_version=1,
        event_id=event_id,
        workspace_id=workspace_id,
        project_id=project_id,
        received_at=now,
        payload=payload,
    )


@pytest.mark.asyncio
async def test_new_issue_publishes_exactly_one_issue_created(sample_envelope, monkeypatch):
    publisher = FakeIssueEventPublisher()
    fake_session = FakeSession(is_new=True)

    # Mock ErrorsRepository
    mock_issue_id = uuid4()
    mock_repo = AsyncMock()
    mock_repo.upsert_issue.return_value = (mock_issue_id, True)  # is_new = True
    mock_repo.insert_event.return_value = True
    mock_repo.bump_issue_counters.return_value = None

    monkeypatch.setattr("app.errors.service.ErrorsRepository", lambda session: mock_repo)

    def session_factory():
        return fake_session

    service = ErrorsService(session_factory=session_factory, publisher=publisher)
    result = await service.process_event(sample_envelope)

    assert result.is_new is True
    assert fake_session.committed is True
    assert len(publisher.published) == 1

    event = publisher.published[0]
    assert event.event_type == "issue.created"
    assert event.workspace_id == sample_envelope.workspace_id
    assert event.project_id == sample_envelope.project_id
    assert event.payload.issue_id == mock_issue_id
    assert event.payload.level == "error"
    assert event.payload.environment == "production"
    assert event.payload.release == "v1.0.0"


@pytest.mark.asyncio
async def test_repeat_occurrence_of_existing_issue_publishes_nothing(sample_envelope, monkeypatch):
    publisher = FakeIssueEventPublisher()
    fake_session = FakeSession(is_new=False)

    mock_issue_id = uuid4()
    mock_repo = AsyncMock()
    mock_repo.upsert_issue.return_value = (mock_issue_id, False)  # is_new = False
    mock_repo.insert_event.return_value = True
    mock_repo.bump_issue_counters.return_value = None

    monkeypatch.setattr("app.errors.service.ErrorsRepository", lambda session: mock_repo)

    def session_factory():
        return fake_session

    service = ErrorsService(session_factory=session_factory, publisher=publisher)
    result = await service.process_event(sample_envelope)

    assert result.is_new is False
    assert fake_session.committed is True
    assert len(publisher.published) == 0


@pytest.mark.asyncio
async def test_publisher_failure_does_not_corrupt_or_fail_committed_issue_write(sample_envelope, monkeypatch):
    publisher = FakeIssueEventPublisher(should_fail=True)
    fake_session = FakeSession(is_new=True)

    mock_issue_id = uuid4()
    mock_repo = AsyncMock()
    mock_repo.upsert_issue.return_value = (mock_issue_id, True)  # is_new = True
    mock_repo.insert_event.return_value = True
    mock_repo.bump_issue_counters.return_value = None

    monkeypatch.setattr("app.errors.service.ErrorsRepository", lambda session: mock_repo)

    def session_factory():
        return fake_session

    service = ErrorsService(session_factory=session_factory, publisher=publisher)
    # Should not raise exception
    result = await service.process_event(sample_envelope)

    assert result.is_new is True
    assert fake_session.committed is True
    assert fake_session.rolled_back is False
