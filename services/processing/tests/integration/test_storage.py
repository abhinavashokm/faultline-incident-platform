import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors.repository import ErrorsRepository
from app.errors.schemas import ErrorEventPayload, EventEnvelope, StackFrame
from app.errors.service import ErrorsService


def make_envelope(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    event_id: uuid.UUID | None = None,
    occurred_at: datetime | None = None,
    exception_type: str = "ValueError",
    message: str = "test error",
    stack_frames: list[StackFrame] | None = None,
    release: str | None = "v1.0.0",
) -> EventEnvelope[ErrorEventPayload]:
    eid = event_id or uuid.uuid4()
    occ = occurred_at or datetime.now(timezone.utc)
    frames = stack_frames if stack_frames is not None else [
        StackFrame(file="app/test.py", function="do_thing", line=10, in_app=True)
    ]

    payload = ErrorEventPayload(
        event_id=eid,
        occurred_at=occ,
        exception_type=exception_type,
        message=message,
        stack_frames=frames,
        event_type="error",
        level="error",
        release=release,
    )
    return EventEnvelope[ErrorEventPayload](
        schema_version=1,
        event_id=eid,
        workspace_id=workspace_id,
        project_id=project_id,
        received_at=datetime.now(timezone.utc),
        payload=payload,
    )


@pytest.mark.asyncio
async def test_first_event_creates_issue_occurrence_count_1(
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    service = ErrorsService(session_factory)
    occurred_at = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    envelope = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        occurred_at=occurred_at,
        release="v1.0.0",
        message="first event message",
    )

    result = await service.process_event(envelope)
    assert result.is_new is True
    assert result.inserted is True

    async with session_factory() as session:
        repo = ErrorsRepository(session)
        issue = await repo.get_issue(result.issue_id)
        assert issue is not None
        assert issue.occurrence_count == 1
        assert issue.affected_users_count == 0
        assert issue.first_seen_at == occurred_at
        assert issue.last_seen_at == occurred_at
        assert issue.first_release == "v1.0.0"
        assert issue.last_release == "v1.0.0"
        assert issue.title == "ValueError: first event message"

        count = await repo.count_events_for_issue(result.issue_id)
        assert count == 1


@pytest.mark.asyncio
async def test_second_event_same_fingerprint_increments_occurrence_count(
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    service = ErrorsService(session_factory)
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

    env1 = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        occurred_at=t1,
        release="v1.0.0",
    )
    res1 = await service.process_event(env1)
    assert res1.is_new is True

    env2 = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        occurred_at=t2,
        release="v1.1.0",
    )
    res2 = await service.process_event(env2)
    assert res2.is_new is False
    assert res2.inserted is True
    assert res2.issue_id == res1.issue_id

    async with session_factory() as session:
        repo = ErrorsRepository(session)
        issue = await repo.get_issue(res1.issue_id)
        assert issue is not None
        assert issue.occurrence_count == 2
        assert issue.first_seen_at == t1
        assert issue.last_seen_at == t2
        assert issue.first_release == "v1.0.0"
        assert issue.last_release == "v1.1.0"

        count = await repo.count_events_for_issue(res1.issue_id)
        assert count == 2


@pytest.mark.asyncio
async def test_same_event_id_delivered_twice_deduplicates(
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    service = ErrorsService(session_factory)
    event_id = uuid.uuid4()
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    envelope = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        event_id=event_id,
        occurred_at=t1,
        release="v1.0.0",
    )

    res1 = await service.process_event(envelope)
    assert res1.inserted is True

    # Redeliver exact same event
    res2 = await service.process_event(envelope)
    assert res2.inserted is False
    assert res2.issue_id == res1.issue_id

    async with session_factory() as session:
        repo = ErrorsRepository(session)
        issue = await repo.get_issue(res1.issue_id)
        assert issue is not None
        assert issue.occurrence_count == 1
        assert issue.first_seen_at == t1
        assert issue.last_seen_at == t1

        count = await repo.count_events_for_issue(res1.issue_id)
        assert count == 1


@pytest.mark.asyncio
async def test_events_with_different_fingerprints_create_different_issues(
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    service = ErrorsService(session_factory)

    env_a = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        exception_type="ZeroDivisionError",
        stack_frames=[StackFrame(file="calc.py", function="div", line=5, in_app=True)],
    )
    env_b = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        exception_type="KeyError",
        stack_frames=[StackFrame(file="lookup.py", function="get_val", line=12, in_app=True)],
    )

    res_a = await service.process_event(env_a)
    res_b = await service.process_event(env_b)

    assert res_a.issue_id != res_b.issue_id

    async with session_factory() as session:
        repo = ErrorsRepository(session)
        issue_a = await repo.get_issue(res_a.issue_id)
        issue_b = await repo.get_issue(res_b.issue_id)
        assert issue_a is not None and issue_a.occurrence_count == 1
        assert issue_b is not None and issue_b.occurrence_count == 1


@pytest.mark.asyncio
async def test_same_fingerprint_in_two_projects_creates_two_issues(
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
):
    service = ErrorsService(session_factory)
    proj1 = uuid.uuid4()
    proj2 = uuid.uuid4()

    env1 = make_envelope(workspace_id=test_workspace_id, project_id=proj1)
    env2 = make_envelope(workspace_id=test_workspace_id, project_id=proj2)

    res1 = await service.process_event(env1)
    res2 = await service.process_event(env2)

    assert res1.issue_id != res2.issue_id
    assert res1.project_id == proj1
    assert res2.project_id == proj2


@pytest.mark.asyncio
async def test_two_concurrent_processors_produce_exactly_one_issue(
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    service = ErrorsService(session_factory)

    env1 = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        event_id=uuid.uuid4(),
        exception_type="ConcurrentTestError",
        stack_frames=[StackFrame(file="race.py", function="contend", line=1, in_app=True)],
    )
    env2 = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        event_id=uuid.uuid4(),
        exception_type="ConcurrentTestError",
        stack_frames=[StackFrame(file="race.py", function="contend", line=1, in_app=True)],
    )

    res1, res2 = await asyncio.gather(
        service.process_event(env1),
        service.process_event(env2),
    )

    assert res1.issue_id == res2.issue_id

    async with session_factory() as session:
        repo = ErrorsRepository(session)
        issue = await repo.get_issue(res1.issue_id)
        assert issue is not None
        assert issue.occurrence_count == 2

        count = await repo.count_events_for_issue(res1.issue_id)
        assert count == 2


@pytest.mark.asyncio
async def test_out_of_order_older_event_moves_first_seen_back(
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    service = ErrorsService(session_factory)
    t_newer = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t_older = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

    # First event received is newer
    env_newer = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        occurred_at=t_newer,
        release="v2.0.0",
    )
    res_newer = await service.process_event(env_newer)

    # Second event received is older (out-of-order delivery)
    env_older = make_envelope(
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        occurred_at=t_older,
        release="v1.0.0",
    )
    res_older = await service.process_event(env_older)

    assert res_newer.issue_id == res_older.issue_id

    async with session_factory() as session:
        repo = ErrorsRepository(session)
        issue = await repo.get_issue(res_newer.issue_id)
        assert issue is not None
        assert issue.occurrence_count == 2
        # first_seen_at moved back to the older timestamp
        assert issue.first_seen_at == t_older
        # last_seen_at did NOT move back
        assert issue.last_seen_at == t_newer
        # last_release remains the release from the newest timestamp
        assert issue.last_release == "v2.0.0"

