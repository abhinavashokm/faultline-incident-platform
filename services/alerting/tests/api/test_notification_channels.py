import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_channel_happy_path(client: AsyncClient, test_project_id: uuid.UUID):
    payload = {
        "name": "Dev On-Call",
        "channel_type": "email",
        "destination": "devs@faultline.io",
        "enabled": True,
    }
    response = await client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Dev On-Call"
    assert data["channel_type"] == "email"
    assert data["destination"] == "devs@faultline.io"
    assert data["enabled"] is True
    assert "id" in data
    assert "created_at" in data
    # Ensure credentials and secrets are NEVER returned in response
    assert "credentials_encrypted" not in data
    assert "secret_reference" not in data


@pytest.mark.asyncio
async def test_create_channel_bad_email(client: AsyncClient, test_project_id: uuid.UUID):
    payload = {
        "name": "Ops Team",
        "channel_type": "email",
        "destination": "not-a-valid-email",
        "enabled": True,
    }
    response = await client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json=payload,
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_create_channel_unsupported_type(client: AsyncClient, test_project_id: uuid.UUID):
    payload = {
        "name": "Slack Alerting",
        "channel_type": "slack",
        "destination": "https://hooks.slack.com/services/xxx",
        "enabled": True,
    }
    response = await client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json=payload,
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_create_channel_unauthenticated(unauth_client: AsyncClient, test_project_id: uuid.UUID):
    payload = {
        "name": "Security Team",
        "channel_type": "email",
        "destination": "sec@faultline.io",
    }
    response = await unauth_client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json=payload,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_channels_empty(client: AsyncClient):
    random_project_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/projects/{random_project_id}/notification-channels"
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_channels_returns_created(client: AsyncClient, test_project_id: uuid.UUID):
    payload1 = {
        "name": "Team Primary",
        "channel_type": "email",
        "destination": "team-primary@faultline.io",
        "enabled": True,
    }
    payload2 = {
        "name": "Team Secondary",
        "channel_type": "email",
        "destination": "team-secondary@faultline.io",
        "enabled": False,
    }

    res1 = await client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json=payload1,
    )
    assert res1.status_code == 201

    res2 = await client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json=payload2,
    )
    assert res2.status_code == 201

    list_res = await client.get(
        f"/api/v1/projects/{test_project_id}/notification-channels"
    )
    assert list_res.status_code == 200
    channels = list_res.json()
    assert len(channels) >= 2
    # Verify shape of items
    for item in channels:
        assert "credentials_encrypted" not in item
        assert "secret_reference" not in item
        assert "id" in item
        assert "name" in item
        assert "destination" in item


@pytest.mark.asyncio
async def test_list_channels_project_isolation(client: AsyncClient):
    project_a = uuid.uuid4()
    project_b = uuid.uuid4()

    await client.post(
        f"/api/v1/projects/{project_a}/notification-channels",
        json={
            "name": "Project A Channel",
            "channel_type": "email",
            "destination": "project-a@faultline.io",
            "enabled": True,
        },
    )

    await client.post(
        f"/api/v1/projects/{project_b}/notification-channels",
        json={
            "name": "Project B Channel",
            "channel_type": "email",
            "destination": "project-b@faultline.io",
            "enabled": True,
        },
    )

    res_a = await client.get(f"/api/v1/projects/{project_a}/notification-channels")
    assert res_a.status_code == 200
    channels_a = res_a.json()
    assert all(c["name"] == "Project A Channel" for c in channels_a)

    res_b = await client.get(f"/api/v1/projects/{project_b}/notification-channels")
    assert res_b.status_code == 200
    channels_b = res_b.json()
    assert all(c["name"] == "Project B Channel" for c in channels_b)
