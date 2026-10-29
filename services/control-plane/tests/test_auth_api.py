import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.security import create_access_token, decode_access_token


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient) -> None:
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


@pytest.mark.asyncio
async def test_signup_duplicate_email_different_casing(client: AsyncClient) -> None:
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
async def test_login_success(client: AsyncClient, db_session: AsyncSession) -> None:
    signup_payload = {
        "email": "login_user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Login User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_resp.status_code == 201
    user_id = signup_resp.json()["id"]

    login_payload = {
        "email": "login_user@example.com",
        "password": "ChangeMe-Strong-Password",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200

    data = login_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 15 * 60

    payload = decode_access_token(data["access_token"])
    assert payload["sub"] == user_id

    # Verify last_login_at was updated in the DB
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    assert user.last_login_at is not None


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
async def test_login_suspended_user(client: AsyncClient, db_session: AsyncSession) -> None:
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
async def test_me_with_valid_token(client: AsyncClient) -> None:
    signup_payload = {
        "email": "me_user@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Me User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = signup_resp.json()["id"]

    login_payload = {
        "email": "me_user@example.com",
        "password": "ChangeMe-Strong-Password",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    token = login_resp.json()["access_token"]

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
    assert data["workspaces"] == []
    assert "email_verified_at" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_me_with_expired_token(client: AsyncClient) -> None:
    signup_payload = {
        "email": "expired@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Expired User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = signup_resp.json()["id"]

    expired_token = create_access_token(
        user_id=user_id,
        ttl=timedelta(seconds=-10),
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_me_for_deleted_user(client: AsyncClient, db_session: AsyncSession) -> None:
    signup_payload = {
        "email": "deleted@example.com",
        "password": "ChangeMe-Strong-Password",
        "full_name": "Deleted User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "deleted@example.com", "password": "ChangeMe-Strong-Password"},
    )
    token = login_resp.json()["access_token"]

    # Mark user as deleted in DB
    stmt = select(User).where(User.id == user_id)
    user = (await db_session.execute(stmt)).scalar_one()
    user.status = "deleted"
    await db_session.commit()

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"

