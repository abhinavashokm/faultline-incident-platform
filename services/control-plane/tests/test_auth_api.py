import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from faultline_auth import JwksKeyProvider, TokenVerifier
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshSession, RefreshToken, User
from app.auth.security import create_access_token
from app.core.config import settings
from app.workspaces.models import Workspace, WorkspaceMember


@pytest.mark.asyncio
async def test_signup_creates_workspace_and_owner(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    payload = {
        "email": "Developer@Example.com ",
        "password": "ChangeMe-Strong-Password",
        "full_name": " Demo Developer ",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "developer@example.com"
    assert data["full_name"] == "Demo Developer"
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data
    assert "password_hash" not in data

    user_id = uuid.UUID(data["id"])
    assert "workspace" in data
    ws_data = data["workspace"]
    assert ws_data["name"] == "Demo Developer's workspace"
    assert ws_data["slug"] == "demo-developer-s-workspace"
    assert "id" in ws_data
    workspace_id = uuid.UUID(ws_data["id"])

    # Verify database state
    ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
    ws = (await db_session.execute(ws_stmt)).scalar_one()
    assert ws.name == "Demo Developer's workspace"
    assert ws.created_by == user_id

    member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    member = (await db_session.execute(member_stmt)).scalar_one()
    assert member.role == "owner"
    assert member.invited_by is None


@pytest.mark.asyncio
async def test_slug_unique_when_two_users_have_same_name(
    client: AsyncClient,
) -> None:
    payload1 = {
        "email": "alice1@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Alice Smith",
    }
    resp1 = await client.post("/api/v1/auth/signup", json=payload1)
    assert resp1.status_code == 201
    slug1 = resp1.json()["workspace"]["slug"]
    assert slug1 == "alice-smith-s-workspace"

    payload2 = {
        "email": "alice2@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Alice Smith",
    }
    resp2 = await client.post("/api/v1/auth/signup", json=payload2)
    assert resp2.status_code == 201
    slug2 = resp2.json()["workspace"]["slug"]

    assert slug1 != slug2
    assert slug2.startswith("alice-smith-s-workspace-")
    # Suffix is '-' plus 4 hex chars
    assert len(slug2) == len(slug1) + 5


@pytest.mark.asyncio
async def test_signup_duplicate_email_different_casing(
    client: AsyncClient,
) -> None:
    first_payload = {
        "email": "user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "First User",
    }
    resp1 = await client.post("/api/v1/auth/signup", json=first_payload)
    assert resp1.status_code == 201

    second_payload = {
        "email": "USER@EXAMPLE.COM",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Second User",
    }
    resp2 = await client.post("/api/v1/auth/signup", json=second_payload)
    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_signup_short_password(client: AsyncClient) -> None:
    payload = {
        "email": "valid@example.com",
        "password": "short",
        "full_name": "Valid User",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_invalid_email(client: AsyncClient) -> None:
    payload = {
        "email": "not-an-email",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Valid User",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success_and_token_claims(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    signup_payload = {
        "email": "login_user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Login User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_resp.status_code == 201
    user_id = signup_resp.json()["id"]
    workspace_id = signup_resp.json()["workspace"]["id"]

    login_payload = {
        "email": "login_user@example.com",
        "password": "ChangeMe-Strong-Password",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200

    data = login_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 15 * 60
    assert data["workspace"] is not None
    assert data["workspace"]["id"] == workspace_id
    assert data["workspace"]["role"] == "owner"

    # Decode and check claims
    access_token = data["access_token"]
    unverified = jwt.decode(access_token, options={"verify_signature": False})
    assert unverified["sub"] == user_id
    assert unverified["workspace_id"] == workspace_id
    assert unverified["role"] == "owner"
    assert unverified["type"] == "access"
    assert "sid" in unverified
    assert "jti" in unverified
    assert unverified["iss"] == settings.jwt_issuer
    assert unverified["aud"] == settings.jwt_audience

    # Verify last_login_at in DB
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    user = (await db_session.execute(stmt)).scalar_one()
    assert user.last_login_at is not None

    # Verify refresh session exists in DB
    sess_stmt = select(RefreshSession).where(RefreshSession.id == uuid.UUID(unverified["sid"]))
    sess = (await db_session.execute(sess_stmt)).scalar_one()
    assert sess.user_id == uuid.UUID(user_id)
    assert sess.revoked_at is None


@pytest.mark.asyncio
async def test_user_without_membership_gets_token_without_workspace_claims(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    signup_payload = {
        "email": "nomember@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "No Member",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    # Remove workspace membership from DB
    member_stmt = select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
    members = (await db_session.execute(member_stmt)).scalars().all()
    for m in members:
        await db_session.delete(m)
    await db_session.commit()

    # Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nomember@example.com", "password": "ChangeMe-Strong-Password"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["workspace"] is None

    unverified = jwt.decode(data["access_token"], options={"verify_signature": False})
    assert unverified["sub"] == str(user_id)
    assert "workspace_id" not in unverified
    assert "role" not in unverified
    assert unverified["type"] == "access"
    assert "sid" in unverified


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    signup_payload = {
        "email": "wrongpass@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Wrong Pass User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    login_payload = {
        "email": "wrongpass@example.com",
        "password": "IncorrectPassword123",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient) -> None:
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "ChangeMe-Strong-Password",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_login_suspended_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    signup_payload = {
        "email": "suspended@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Suspended User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    # Update status to suspended
    stmt = select(User).where(User.id == user_id)
    user = (await db_session.execute(stmt)).scalar_one()
    user.status = "suspended"
    await db_session.commit()

    login_payload = {
        "email": "suspended@example.com",
        "password": "ChangeMe-Strong-Password",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_old_token_invalidation(
    client: AsyncClient,
) -> None:
    signup_payload = {
        "email": "refresh_user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Refresh User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh_user@example.com", "password": "ChangeMe-Strong-Password"},
    )
    assert login_resp.status_code == 200
    rt1 = login_resp.json()["refresh_token"]

    # Refresh
    ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert ref_resp.status_code == 200
    data = ref_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    rt2 = data["refresh_token"]
    assert rt2 != rt1

    # Old refresh token rt1 no longer works
    ref_resp_old = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert ref_resp_old.status_code == 401
    assert ref_resp_old.json()["detail"] == "Invalid refresh token"
    assert ref_resp_old.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_refresh_token_reuse_revokes_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    signup_payload = {
        "email": "reuse_user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Reuse User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "reuse_user@example.com", "password": "ChangeMe-Strong-Password"},
    )
    rt1 = login_resp.json()["refresh_token"]

    # First refresh: rt1 -> rt2
    ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert ref_resp.status_code == 200
    rt2 = ref_resp.json()["refresh_token"]

    # REUSE: Use rt1 again
    reuse_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["detail"] == "Invalid refresh token"

    # Whole session must now be revoked, so newest token rt2 also fails
    new_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt2})
    assert new_resp.status_code == 401
    assert new_resp.json()["detail"] == "Invalid refresh token"

    # Verify session revoked_reason is 'reuse_detected'
    unverified = jwt.decode(ref_resp.json()["access_token"], options={"verify_signature": False})
    sid = uuid.UUID(unverified["sid"])
    sess = (await db_session.execute(select(RefreshSession).where(RefreshSession.id == sid))).scalar_one()
    assert sess.revoked_at is not None
    assert sess.revoked_reason == "reuse_detected"


@pytest.mark.asyncio
async def test_logout_revokes_session(client: AsyncClient) -> None:
    signup_payload = {
        "email": "logout_user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Logout User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "logout_user@example.com", "password": "ChangeMe-Strong-Password"},
    )
    rt = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": rt})
    assert logout_resp.status_code == 204

    # Idempotent logout with same or unknown token returns 204
    logout_resp2 = await client.post("/api/v1/auth/logout", json={"refresh_token": rt})
    assert logout_resp2.status_code == 204
    logout_resp3 = await client.post("/api/v1/auth/logout", json={"refresh_token": "unknown-token"})
    assert logout_resp3.status_code == 204

    # Refresh after logout fails
    ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert ref_resp.status_code == 401
    assert ref_resp.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_expired_refresh_token_fails(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    signup_payload = {
        "email": "expired_rt@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Expired RT User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "expired_rt@example.com", "password": "ChangeMe-Strong-Password"},
    )
    rt = login_resp.json()["refresh_token"]

    # Expire the token in DB
    unverified = jwt.decode(login_resp.json()["access_token"], options={"verify_signature": False})
    sid = uuid.UUID(unverified["sid"])
    tokens = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.session_id == sid))
    ).scalars().all()
    past = datetime.now(timezone.utc) - timedelta(days=1)
    for t in tokens:
        t.expires_at = past
    await db_session.commit()

    ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert ref_resp.status_code == 401
    assert ref_resp.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_disabled_user_cannot_refresh(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    signup_payload = {
        "email": "disabled_rt@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Disabled RT User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "disabled_rt@example.com", "password": "ChangeMe-Strong-Password"},
    )
    rt = login_resp.json()["refresh_token"]

    # Suspend user
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    user.status = "suspended"
    await db_session.commit()

    ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert ref_resp.status_code == 401
    assert ref_resp.json()["detail"] == "Invalid refresh token"

    # Check session revoked with user_disabled
    unverified = jwt.decode(login_resp.json()["access_token"], options={"verify_signature": False})
    sid = uuid.UUID(unverified["sid"])
    sess = (await db_session.execute(select(RefreshSession).where(RefreshSession.id == sid))).scalar_one()
    assert sess.revoked_at is not None
    assert sess.revoked_reason == "user_disabled"


@pytest.mark.asyncio
async def test_refresh_picks_up_changed_role(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    signup_payload = {
        "email": "role_change@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Role Change User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "role_change@example.com", "password": "ChangeMe-Strong-Password"},
    )
    rt = login_resp.json()["refresh_token"]
    assert login_resp.json()["workspace"]["role"] == "owner"

    # Update role to admin in DB
    member = (
        await db_session.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
        )
    ).scalar_one()
    member.role = "admin"
    await db_session.commit()

    # Refresh
    ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert ref_resp.status_code == 200
    data = ref_resp.json()
    assert data["workspace"]["role"] == "admin"

    unverified = jwt.decode(data["access_token"], options={"verify_signature": False})
    assert unverified["role"] == "admin"


@pytest.mark.asyncio
async def test_me_with_valid_and_invalid_token(client: AsyncClient) -> None:
    signup_payload = {
        "email": "me_user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Me User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = signup_resp.json()["id"]
    workspace_id = signup_resp.json()["workspace"]["id"]

    login_payload = {
        "email": "me_user@example.com",
        "password": "ChangeMe-Strong-Password",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    token = login_resp.json()["access_token"]

    # 1. Valid token
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "me_user@example.com"
    assert data["full_name"] == "Me User"
    assert data["status"] == "active"
    assert data["workspace"]["id"] == workspace_id
    assert data["workspace"]["role"] == "owner"
    assert len(data["memberships"]) == 1
    assert data["memberships"][0]["workspace_id"] == workspace_id
    assert data["memberships"][0]["role"] == "owner"

    # 2. Missing token
    resp_no_token = await client.get("/api/v1/auth/me")
    assert resp_no_token.status_code == 401
    assert resp_no_token.headers.get("www-authenticate") == "Bearer"

    # 3. Invalid / garbage token
    resp_bad_token = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert resp_bad_token.status_code == 401
    assert resp_bad_token.headers.get("www-authenticate") == "Bearer"

    # 4. Expired token (expired past the 30-second leeway)
    expired_token = create_access_token(
        user_id=user_id,
        ttl=timedelta(seconds=-60),
    )
    resp_expired = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp_expired.status_code == 401
    assert resp_expired.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_jwks_endpoint_and_token_verification(client: AsyncClient) -> None:
    # 1. Fetch JWKS from endpoint
    jwks_resp = await client.get("/.well-known/jwks.json")
    assert jwks_resp.status_code == 200
    assert "public, max-age=" in jwks_resp.headers.get("cache-control", "")

    jwks_data = jwks_resp.json()
    assert "keys" in jwks_data
    assert len(jwks_data["keys"]) == 1

    key = jwks_data["keys"][0]
    assert key["kty"] == "RSA"
    assert key["use"] == "sig"
    assert key["alg"] == "RS256"
    assert key["kid"] == settings.jwt_key_id
    assert "n" in key
    assert "e" in key

    # 2. Assert no private fields are leaked
    for private_field in ["d", "p", "q", "dp", "dq", "qi", "oth"]:
        assert private_field not in key

    # 3. Issue a token and verify kid matches
    signup_payload = {
        "email": "jwks_user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "JWKS User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "jwks_user@example.com", "password": "ChangeMe-Strong-Password"},
    )
    access_token = login_resp.json()["access_token"]
    header = jwt.get_unverified_header(access_token)
    assert header["kid"] == key["kid"]

    # 4. Verify token using only the JWKS output with JwksKeyProvider
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=jwks_data))
    async with httpx.AsyncClient(transport=transport) as jwks_client:
        provider = JwksKeyProvider(
            "https://control.internal/.well-known/jwks.json",
            client=jwks_client,
        )
        verifier = TokenVerifier(
            provider,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        ctx = await verifier.verify(access_token)
        assert ctx.token_id is not None
        assert ctx.workspace_id is not None
        assert ctx.role == "owner"
