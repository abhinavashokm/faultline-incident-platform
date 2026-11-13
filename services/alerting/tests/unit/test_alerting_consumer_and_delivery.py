import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from faultline_events import IssueCreatedEvent, IssueCreatedPayload
from app.alerts.consumer_handler import (
    build_alerts_consumer_handler,
    registry,
)
from app.alerts.evaluation_service import AlertEvaluationService
from app.alerts.matcher import NewIssueMatcher
from app.alerts.models import AlertRule, ProcessedEvent
from app.delivery.email import EmailSender
from app.delivery.models import Delivery, NotificationChannel
from app.delivery.outbox_processor import OutboxDeliveryService
from app.delivery.senders import EmailChannelSender
from app.messaging.consumer import PermanentError


class FakeEmailSender:
    def __init__(self, should_fail: bool = False) -> None:
        self.sent_messages: list[dict] = []
        self.should_fail = should_fail

    async def send(self, to_email: str, subject: str, text_body: str, html_body: str) -> None:
        if self.should_fail:
            raise RuntimeError("SMTP connection timeout")
        self.sent_messages.append({
            "to_email": to_email,
            "subject": subject,
            "text_body": text_body,
            "html_body": html_body,
        })


class FakeAsyncSession:
    def __init__(self) -> None:
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
def sample_issue_created_event() -> IssueCreatedEvent:
    event_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    issue_id = uuid4()
    now = datetime.now(timezone.utc)

    payload = IssueCreatedPayload(
        issue_id=issue_id,
        title="ZeroDivisionError: division by zero",
        level="error",
        environment="production",
        release="v2.1.0",
        first_seen=now,
    )
    return IssueCreatedEvent(
        event_id=event_id,
        workspace_id=workspace_id,
        project_id=project_id,
        occurred_at=now,
        payload=payload,
    )


# 1. Matching rule creates one alert and delivery jobs for its channels
@pytest.mark.asyncio
async def test_matching_rule_creates_alert_and_delivery_jobs(sample_issue_created_event, monkeypatch):
    fake_session = FakeAsyncSession()
    def mock_session_factory():
        return fake_session

    rule_id = uuid4()
    channel_id = uuid4()
    fake_channel = NotificationChannel(
        id=channel_id,
        project_id=sample_issue_created_event.project_id,
        name="Team Email",
        channel_type="email",
        destination="ops@example.com",
        enabled=True,
    )
    fake_assoc = MagicMock()
    fake_assoc.channel = fake_channel

    fake_rule = AlertRule(
        id=rule_id,
        project_id=sample_issue_created_event.project_id,
        name="Production New Issue Alert",
        rule_type="new_issue",
        environment="production",
        severity="error",
        enabled=True,
        conditions={"level": "error"},
        channel_associations=[fake_assoc],
    )

    mock_eval_repo = AsyncMock()
    mock_eval_repo.record_processed_event.return_value = True  # First time processed
    mock_eval_repo.get_or_create_alert_state.return_value = MagicMock(id=uuid4())
    mock_eval_repo.create_alert.return_value = MagicMock(id=uuid4())
    mock_eval_repo.create_delivery_jobs.return_value = [MagicMock(id=uuid4())]

    mock_rule_repo = AsyncMock()
    mock_rule_repo.list_enabled_by_project.return_value = [fake_rule]

    monkeypatch.setattr("app.alerts.evaluation_service.AlertEvaluationRepository", lambda s: mock_eval_repo)
    monkeypatch.setattr("app.alerts.evaluation_service.AlertRuleRepository", lambda s: mock_rule_repo)

    service = AlertEvaluationService(mock_session_factory)
    processed = await service.handle_issue_created(sample_issue_created_event)

    assert processed is True
    mock_eval_repo.record_processed_event.assert_awaited_once_with(
        event_id=sample_issue_created_event.event_id,
        project_id=sample_issue_created_event.project_id,
        event_type="issue.created",
    )
    mock_eval_repo.create_alert.assert_awaited_once()
    mock_eval_repo.create_delivery_jobs.assert_awaited_once()


# 2. Non-matching rule creates nothing
@pytest.mark.asyncio
async def test_non_matching_rule_creates_nothing(sample_issue_created_event, monkeypatch):
    fake_session = FakeAsyncSession()
    def mock_session_factory():
        return fake_session

    fake_rule = AlertRule(
        id=uuid4(),
        project_id=sample_issue_created_event.project_id,
        name="Staging Alert",
        rule_type="new_issue",
        environment="staging",  # event is production!
        severity="error",
        enabled=True,
        conditions={},
        channel_associations=[],
    )

    mock_eval_repo = AsyncMock()
    mock_eval_repo.record_processed_event.return_value = True
    mock_rule_repo = AsyncMock()
    mock_rule_repo.list_enabled_by_project.return_value = [fake_rule]

    monkeypatch.setattr("app.alerts.evaluation_service.AlertEvaluationRepository", lambda s: mock_eval_repo)
    monkeypatch.setattr("app.alerts.evaluation_service.AlertRuleRepository", lambda s: mock_rule_repo)

    service = AlertEvaluationService(mock_session_factory)
    processed = await service.handle_issue_created(sample_issue_created_event)

    assert processed is True
    mock_eval_repo.create_alert.assert_not_awaited()
    mock_eval_repo.create_delivery_jobs.assert_not_awaited()


# 3. Same event_id delivered twice creates nothing the second time
@pytest.mark.asyncio
async def test_duplicate_event_id_creates_nothing(sample_issue_created_event, monkeypatch):
    fake_session = FakeAsyncSession()
    def mock_session_factory():
        return fake_session

    mock_eval_repo = AsyncMock()
    mock_eval_repo.record_processed_event.return_value = False  # Already processed!
    mock_rule_repo = AsyncMock()

    monkeypatch.setattr("app.alerts.evaluation_service.AlertEvaluationRepository", lambda s: mock_eval_repo)
    monkeypatch.setattr("app.alerts.evaluation_service.AlertRuleRepository", lambda s: mock_rule_repo)

    service = AlertEvaluationService(mock_session_factory)
    processed = await service.handle_issue_created(sample_issue_created_event)

    assert processed is False
    mock_rule_repo.list_enabled_by_project.assert_not_awaited()
    mock_eval_repo.create_alert.assert_not_awaited()


# 4. Unknown event_type is skipped and returns without exception
@pytest.mark.asyncio
async def test_unknown_event_type_is_skipped():
    mock_service = AsyncMock()
    handler = build_alerts_consumer_handler(mock_service)

    raw_event = json.dumps({
        "event_id": str(uuid4()),
        "event_type": "unknown.custom_event",
        "workspace_id": str(uuid4()),
        "project_id": str(uuid4()),
        "payload": {},
    }).encode("utf-8")

    # Should not raise exception
    await handler(raw_event, "issue-events", 0, 100)
    mock_service.handle_issue_created.assert_not_awaited()


# 5. Malformed message raises PermanentError, and transient DB error propagates
@pytest.mark.asyncio
async def test_malformed_message_raises_permanent_error():
    mock_service = AsyncMock()
    handler = build_alerts_consumer_handler(mock_service)

    # Missing event_type
    with pytest.raises(PermanentError):
        await handler(b'{"foo": "bar"}', "issue-events", 0, 1)

    # Invalid JSON
    with pytest.raises(PermanentError):
        await handler(b'not a json', "issue-events", 0, 2)

    # Invalid payload for issue.created
    bad_payload = json.dumps({
        "event_id": str(uuid4()),
        "event_type": "issue.created",
        "workspace_id": str(uuid4()),
        "project_id": str(uuid4()),
        "payload": {"invalid": "missing required fields"},
    }).encode("utf-8")
    with pytest.raises(PermanentError):
        await handler(bad_payload, "issue-events", 0, 3)


@pytest.mark.asyncio
async def test_transient_db_error_propagates_without_permanent_error(sample_issue_created_event):
    mock_service = AsyncMock()
    mock_service.handle_issue_created.side_effect = RuntimeError("Database connection lost")
    handler = build_alerts_consumer_handler(mock_service)

    valid_payload = sample_issue_created_event.model_dump_json().encode("utf-8")

    # Transient error should propagate directly so Kafka consumer loop redelivers without committing offset
    with pytest.raises(RuntimeError, match="Database connection lost"):
        await handler(valid_payload, "issue-events", 0, 4)


# 6. Email delivery & failure handling
@pytest.mark.asyncio
async def test_email_delivery_and_failure_recording(monkeypatch):
    fake_sender = FakeEmailSender(should_fail=False)
    email_sender_handler = EmailChannelSender(fake_sender)

    fake_channel = NotificationChannel(
        id=uuid4(),
        project_id=uuid4(),
        name="Alerts Channel",
        channel_type="email",
        destination="alert-recipient@example.com",
        enabled=True,
    )
    fake_delivery = Delivery(
        id=uuid4(),
        project_id=fake_channel.project_id,
        alert_id=uuid4(),
        channel_id=fake_channel.id,
        idempotency_key="key1",
        status="pending",
        payload={
            "project_id": str(fake_channel.project_id),
            "title": "IndexError: list index out of range\r\nBcc: evil@attacker.com",
            "level": "error",
            "environment": "production",
            "release": "v1.0.0",
            "first_seen": "2026-11-13T09:00:00Z",
            "issue_id": str(uuid4()),
        },
    )

    # Test sender formatting
    await email_sender_handler.send(fake_channel, fake_delivery)
    assert len(fake_sender.sent_messages) == 1
    msg = fake_sender.sent_messages[0]
    assert msg["to_email"] == "alert-recipient@example.com"
    # Verify CR/LF stripped from subject
    assert "\r" not in msg["subject"]
    assert "\n" not in msg["subject"]
    assert "evil@attacker.com" in msg["subject"]
    assert "[Faultline] New issue in" in msg["subject"]

    # Test outbox processor with fake repository
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    fake_delivery.channel = fake_channel
    mock_delivery_repo = AsyncMock()
    mock_delivery_repo.get_pending_deliveries.return_value = [fake_delivery]

    monkeypatch.setattr("app.delivery.outbox_processor.DeliveryRepository", lambda s: mock_delivery_repo)

    processor = OutboxDeliveryService(
        session_factory=mock_session_factory,
        senders={"email": email_sender_handler},
    )
    count = await processor.process_batch(limit=10)
    assert count == 1
    mock_delivery_repo.record_attempt.assert_awaited_once_with(
        fake_delivery,
        status="success",
        response_summary="Message sent successfully",
    )

    # Test outbox processor sender failure
    failing_sender = FakeEmailSender(should_fail=True)
    failing_email_handler = EmailChannelSender(failing_sender)
    mock_delivery_repo.record_attempt.reset_mock()

    failing_processor = OutboxDeliveryService(
        session_factory=mock_session_factory,
        senders={"email": failing_email_handler},
    )
    count = await failing_processor.process_batch(limit=10)
    assert count == 1
    mock_delivery_repo.record_attempt.assert_awaited_once_with(
        fake_delivery,
        status="failure",
        error_message="SMTP connection timeout",
    )
