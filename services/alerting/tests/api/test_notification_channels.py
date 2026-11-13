import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from faultline_auth import Principal, get_principal
from app.core.db import get_session
from app.delivery.email import get_email_sender
from app.main import create_app
from tests.conftest import FakeEmailSender


@pytest.mark.asyncio
async def test_create_channel_happy_path(
    client: AsyncClient, test_project_id: uuid.UUID, fake_email_sender: FakeEmailSender, auth_principal: Principal
):
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

    # Verify confirmation email was sent
    assert len(fake_email_sender.sent_emails) == 1
    sent = fake_email_sender.sent_emails[0]
    assert sent["to_email"] == "devs@faultline.io"
    assert sent["subject"] == 'Your Faultline notification channel "Dev On-Call" was added'
    assert "Dev On-Call" in sent["text_body"]
    assert str(test_project_id) in sent["text_body"]
    assert str(auth_principal.user_id) in sent["text_body"]
    assert "Status: Enabled" in sent["text_body"]
    assert "If you did not expect this, contact your workspace admin." in sent["text_body"]
    assert "<strong>&quot;Dev On-Call&quot;</strong>" in sent["html_body"] or "Dev On-Call" in sent["html_body"]


@pytest.mark.asyncio
async def test_create_channel_disabled_sends_email_with_disabled_status(
    client: AsyncClient, test_project_id: uuid.UUID, fake_email_sender: FakeEmailSender
):
    payload = {
        "name": "Disabled Alerts",
        "channel_type": "email",
        "destination": "disabled@faultline.io",
        "enabled": False,
    }
    response = await client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json=payload,
    )
    assert response.status_code == 201
    assert len(fake_email_sender.sent_emails) == 1
    sent = fake_email_sender.sent_emails[0]
    assert "Status: Disabled" in sent["text_body"]
    assert "Disabled" in sent["html_body"]


@pytest.mark.asyncio
async def test_create_channel_email_sender_failure_still_returns_201(
    session_factory: async_sessionmaker[AsyncSession],
    auth_principal: Principal,
    test_project_id: uuid.UUID,
):
    app = create_app()

    async def _test_get_session():
        async with session_factory() as session:
            yield session

    failing_sender = FakeEmailSender(should_fail=True)
    app.dependency_overrides[get_session] = _test_get_session
    app.dependency_overrides[get_principal] = lambda: auth_principal
    app.dependency_overrides[get_email_sender] = lambda: failing_sender

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/projects/{test_project_id}/notification-channels",
            json={
                "name": "Reliable Channel",
                "channel_type": "email",
                "destination": "reliable@faultline.io",
                "enabled": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Reliable Channel"


@pytest.mark.asyncio
async def test_create_channel_html_escaping_and_crlf_stripping(
    client: AsyncClient, test_project_id: uuid.UUID, fake_email_sender: FakeEmailSender
):
    payload = {
        "name": "<script>alert('xss')</script>\r\nSubject injection",
        "channel_type": "email",
        "destination": "sec-test@faultline.io",
        "enabled": True,
    }
    response = await client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json=payload,
    )
    assert response.status_code == 201
    assert len(fake_email_sender.sent_emails) == 1
    sent = fake_email_sender.sent_emails[0]

    # Subject must not have CR or LF
    assert "\r" not in sent["subject"]
    assert "\n" not in sent["subject"]
    assert 'Your Faultline notification channel "<script>alert(\'xss\')</script>Subject injection" was added' == sent["subject"]

    # HTML body must have escaped tags
    assert "<script>" not in sent["html_body"]
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in sent["html_body"]


@pytest.mark.asyncio
async def test_create_channel_bad_email(client: AsyncClient, test_project_id: uuid.UUID, fake_email_sender: FakeEmailSender):
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
    # No email should be sent on 422
    assert len(fake_email_sender.sent_emails) == 0


@pytest.mark.asyncio
async def test_create_channel_unsupported_type(client: AsyncClient, test_project_id: uuid.UUID, fake_email_sender: FakeEmailSender):
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
    # No email should be sent on 422 / non-email
    assert len(fake_email_sender.sent_emails) == 0


@pytest.mark.asyncio
async def test_create_channel_unauthenticated(unauth_client: AsyncClient, test_project_id: uuid.UUID, fake_email_sender: FakeEmailSender):
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
    # No email should be sent on 401
    assert len(fake_email_sender.sent_emails) == 0


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
