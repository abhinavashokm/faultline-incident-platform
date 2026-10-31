import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.db import get_session
from app.errors.models import Issue
from app.main import create_app


def make_token(
    key,
    kid="dev-1",
    issuer="faultline-control-plane",
    audience="faultline",
    sub=None,
    workspace_id=None,
    role="owner",
    token_type="access",
    sid=None,
    jti=None,
    exp_delta=timedelta(minutes=15),
    alg="RS256",
):
    now = datetime.now(timezone.utc)
    sub = sub or str(uuid.uuid4())
    jti = jti or str(uuid.uuid4())
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
        "jti": jti,
    }
    if workspace_id is not None:
        payload["workspace_id"] = str(workspace_id)
    if role is not None:
        payload["role"] = role
    if sid is not None:
        payload["sid"] = str(sid)

    headers = {"kid": kid}
    return jwt.encode(payload, key, algorithm=alg, headers=headers)


async def insert_test_issue(
    session_factory: async_sessionmaker[AsyncSession],
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    title: str = "Test Issue",
) -> uuid.UUID:
    issue_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        issue = Issue(
            id=issue_id,
            workspace_id=workspace_id,
            project_id=project_id,
            fingerprint=uuid.uuid4().hex * 2,
            fingerprint_version=1,
            title=title,
            exception_type="TestException",
            culprit="app/test.py:run",
            level="error",
            status="unresolved",
            first_seen_at=now,
            last_seen_at=now,
            occurrence_count=1,
            affected_users_count=0,
            first_release="v1.0.0",
            last_release="v1.0.0",
        )
        session.add(issue)
        await session.commit()
    return issue_id


@pytest_asyncio.fixture
async def real_auth_client(
    session_factory: async_sessionmaker[AsyncSession],
    rsa_keys,
    monkeypatch,
) -> AsyncIterator[AsyncClient]:
    """Client using the REAL get_principal (no get_principal dependency override)."""
    monkeypatch.setattr(settings, "auth_provider", "static")
    monkeypatch.setattr(settings, "auth_issuer", "faultline-control-plane")
    monkeypatch.setattr(settings, "auth_audience", "faultline")
    monkeypatch.setattr(settings, "auth_leeway_seconds", 30)
    monkeypatch.setattr(settings, "auth_public_key_path", rsa_keys["pub_key_path"])
    monkeypatch.setattr(settings, "auth_jwt_key_id", rsa_keys["kid"])

    app = create_app()

    async def _test_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _test_get_session
    # NOTE: get_principal is NOT overridden here! Real verification runs!

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# 1. End-to-end API test with real token verification and tenant isolation
@pytest.mark.asyncio
async def test_e2e_real_auth_workspace_isolation_without_override(
    real_auth_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    rsa_keys,
):
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()
    project_a = uuid.uuid4()
    project_b = uuid.uuid4()

    issue_a = await insert_test_issue(session_factory, ws_a, project_a, title="Issue for Workspace A")
    issue_b = await insert_test_issue(session_factory, ws_b, project_b, title="Issue for Workspace B")

    token_a = make_token(rsa_keys["private_key"], workspace_id=ws_a)
    token_b = make_token(rsa_keys["private_key"], workspace_id=ws_b)

    # Workspace A can list its own issues (200)
    res_list_a = await real_auth_client.get(
        f"/api/v1/projects/{project_a}/issues",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_list_a.status_code == 200
    items_a = res_list_a.json()["items"]
    assert len(items_a) == 1
    assert items_a[0]["id"] == str(issue_a)

    # Workspace A can view its own issue details (200)
    res_detail_a = await real_auth_client.get(
        f"/api/v1/projects/{project_a}/issues/{issue_a}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_detail_a.status_code == 200
    assert res_detail_a.json()["id"] == str(issue_a)

    # Workspace A CANNOT view Workspace B's issue -> 404 (tenant isolation)
    res_cross = await real_auth_client.get(
        f"/api/v1/projects/{project_b}/issues/{issue_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_cross.status_code == 404
    assert res_cross.json()["detail"] == "The requested resource was not found"

    # Workspace B can view its own issue details (200)
    res_detail_b = await real_auth_client.get(
        f"/api/v1/projects/{project_b}/issues/{issue_b}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_detail_b.status_code == 200
    assert res_detail_b.json()["id"] == str(issue_b)

    # Workspace B CANNOT view Workspace A's issue -> 404
    res_cross_b = await real_auth_client.get(
        f"/api/v1/projects/{project_a}/issues/{issue_a}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_cross_b.status_code == 404
    assert res_cross_b.json()["detail"] == "The requested resource was not found"


# 2. Unauthenticated request rejected with 401
@pytest.mark.asyncio
async def test_e2e_unauthenticated_request_rejected(real_auth_client: AsyncClient):
    proj_id = uuid.uuid4()
    res = await real_auth_client.get(f"/api/v1/projects/{proj_id}/issues")
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing or invalid credentials"
    assert res.headers.get("www-authenticate") == "Bearer"


# 3. Expired token rejected with 401
@pytest.mark.asyncio
async def test_e2e_expired_token_rejected(real_auth_client: AsyncClient, rsa_keys, monkeypatch):
    monkeypatch.setattr(settings, "auth_leeway_seconds", 0)
    expired_token = make_token(
        rsa_keys["private_key"],
        workspace_id=uuid.uuid4(),
        exp_delta=timedelta(seconds=-10),
    )
    proj_id = uuid.uuid4()
    res = await real_auth_client.get(
        f"/api/v1/projects/{proj_id}/issues",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing or invalid credentials"


# 4. Tampered token rejected with 401
@pytest.mark.asyncio
async def test_e2e_tampered_token_rejected(real_auth_client: AsyncClient, rsa_keys):
    valid_token = make_token(rsa_keys["private_key"], workspace_id=uuid.uuid4())
    parts = valid_token.split(".")
    tampered_sig = ("X" if parts[2][0] != "X" else "Y") + parts[2][1:]
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    proj_id = uuid.uuid4()
    res = await real_auth_client.get(
        f"/api/v1/projects/{proj_id}/issues",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing or invalid credentials"


# 5. Token missing workspace_id returns 403
@pytest.mark.asyncio
async def test_e2e_missing_workspace_id_returns_403(real_auth_client: AsyncClient, rsa_keys):
    token_without_ws = make_token(rsa_keys["private_key"], workspace_id=None)
    proj_id = uuid.uuid4()
    res = await real_auth_client.get(
        f"/api/v1/projects/{proj_id}/issues",
        headers={"Authorization": f"Bearer {token_without_ws}"},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "You do not have permission to access this resource"


# 6. Token with non-UUID workspace_id returns 403
@pytest.mark.asyncio
async def test_e2e_non_uuid_workspace_id_returns_403(real_auth_client: AsyncClient, rsa_keys):
    token_bad_ws = make_token(rsa_keys["private_key"], workspace_id="not-a-valid-uuid")
    proj_id = uuid.uuid4()
    res = await real_auth_client.get(
        f"/api/v1/projects/{proj_id}/issues",
        headers={"Authorization": f"Bearer {token_bad_ws}"},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "You do not have permission to access this resource"


# 7. App refuses / rejects all requests with 401 when auth is misconfigured
@pytest.mark.asyncio
async def test_e2e_misconfiguration_rejects_requests_with_401(
    session_factory: async_sessionmaker[AsyncSession],
    rsa_keys,
    monkeypatch,
):
    monkeypatch.setattr(settings, "auth_provider", "static")
    monkeypatch.setattr(settings, "auth_public_key_path", "/nonexistent/path/pub.pem")

    app = create_app()

    async def _test_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _test_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = make_token(rsa_keys["private_key"], workspace_id=uuid.uuid4())
        res = await ac.get(
            f"/api/v1/projects/{uuid.uuid4()}/issues",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 401
        assert res.json()["detail"] == "Missing or invalid credentials"


# 8. /health endpoint is unauthenticated
@pytest.mark.asyncio
async def test_e2e_health_remains_unauthenticated(real_auth_client: AsyncClient):
    res = await real_auth_client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
