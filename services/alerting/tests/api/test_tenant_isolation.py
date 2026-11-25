from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from faultline_auth import Principal, get_principal
from faultline_events import IssueCreatedEvent, IssueCreatedPayload
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.alerts.evaluation_service import AlertEvaluationService
from app.alerts.models import Alert, AlertState
from app.core.db import get_session
from app.delivery.models import Delivery
from app.main import create_app


@pytest_asyncio.fixture
async def other_workspace_client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def get_test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    principal = Principal(user_id=uuid4(), workspace_id=uuid4())
    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_principal] = lambda: principal
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_channel_and_rule_isolation(
    client: AsyncClient,
    other_workspace_client: AsyncClient,
    test_workspace_id: UUID,
    test_project_id: UUID,
) -> None:
    channels_url = f"/api/v1/projects/{test_project_id}/notification-channels"
    rules_url = f"/api/v1/projects/{test_project_id}/alert-rules"
    spoofed_workspace_id = str(uuid4())
    response = await client.post(
        channels_url,
        params={"workspace_id": spoofed_workspace_id},
        json={
            "name": "Ops",
            "channel_type": "email",
            "destination": "ops@example.com",
            "workspace_id": spoofed_workspace_id,
        },
    )
    assert response.status_code == 201
    channel = response.json()

    response = await client.get(channels_url, params={"workspace_id": spoofed_workspace_id})
    assert response.status_code == 200
    assert response.json() == [channel]

    response = await other_workspace_client.get(
        channels_url, params={"workspace_id": str(test_workspace_id)}
    )
    assert response.status_code == 200
    assert response.json() == []

    payload = {
        "name": "Issue alert",
        "rule_type": "new_issue",
        "conditions": {},
        "channel_ids": [channel["id"]],
    }
    rejected = await other_workspace_client.post(
        rules_url, json={**payload, "workspace_id": str(test_workspace_id)}
    )
    assert rejected.status_code == 422
    assert isinstance(rejected.json()["detail"], str)
    assert (await other_workspace_client.get(rules_url)).json()["items"] == []

    created = await client.post(rules_url, json=payload)
    assert created.status_code == 201
    rule_url = f"{rules_url}/{created.json()['id']}"
    assert (await other_workspace_client.patch(rule_url, json={"name": "Changed"})).status_code == 404
    assert (await other_workspace_client.delete(rule_url)).status_code == 404

    rejected = await client.patch(
        rule_url, json={"name": "Changed", "channel_ids": [str(uuid4())]}
    )
    assert rejected.status_code == 422
    assert (await client.get(rules_url)).json()["items"] == [created.json()]


@pytest.mark.asyncio
async def test_evaluator_scopes_rules_and_persists_delivery_workspace(
    client: AsyncClient,
    other_workspace_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: UUID,
    test_project_id: UUID,
) -> None:
    project_url = f"/api/v1/projects/{test_project_id}"
    channel = await client.post(
        f"{project_url}/notification-channels",
        json={"name": "Ops", "channel_type": "email", "destination": "ops@example.com"},
    )
    assert channel.status_code == 201
    rule_payload = {"name": "Issue alert", "rule_type": "new_issue", "conditions": {}}
    other_rule = await other_workspace_client.post(f"{project_url}/alert-rules", json=rule_payload)
    assert other_rule.status_code == 201
    rule = await client.post(
        f"{project_url}/alert-rules",
        json={**rule_payload, "channel_ids": [channel.json()["id"]]},
    )
    assert rule.status_code == 201

    event = IssueCreatedEvent(
        event_id=uuid4(),
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        payload=IssueCreatedPayload(
            issue_id=uuid4(),
            title="Test issue",
            level="error",
            first_seen=datetime.now(timezone.utc),
        ),
    )
    assert await AlertEvaluationService(session_factory).handle_issue_created(event)

    async with session_factory() as session:
        alert = (await session.scalars(select(Alert).where(Alert.project_id == test_project_id))).one()
        assert alert.rule_id == UUID(rule.json()["id"])
        assert alert.workspace_id == test_workspace_id
        state = await session.get(AlertState, alert.state_id)
        assert state is not None
        assert state.workspace_id == test_workspace_id
        delivery = (
            await session.scalars(select(Delivery).where(Delivery.project_id == test_project_id))
        ).one()
        assert delivery.alert_id == alert.id
        assert delivery.channel_id == UUID(channel.json()["id"])
        assert delivery.workspace_id == test_workspace_id
