from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from faultline_auth import (
    AuthConfigurationError,
    AuthContext,
    AuthDependencies,
    AuthSettings,
    InvalidToken,
    InvalidWorkspaceClaim,
    KeysUnavailable,
    Principal,
    StaticKeyProvider,
    TokenVerifier,
    build_token_verifier,
    configure_auth,
    get_principal,
    get_token_verifier,
    reset_auth_cache,
)


def make_test_jwt(
    key,
    kid="test-key-1",
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
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": str(sub or uuid.uuid4()),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
        "jti": str(jti or uuid.uuid4()),
    }
    if workspace_id is not None:
        payload["workspace_id"] = str(workspace_id)
    if role is not None:
        payload["role"] = role
    if sid is not None:
        payload["sid"] = str(sid)

    headers = {"kid": kid}
    return jwt.encode(payload, key, algorithm=alg, headers=headers)


# ---------------------------------------------------------------------------
# 1. Settings Validation Tests
# ---------------------------------------------------------------------------


def test_settings_missing_provider():
    with pytest.raises(AuthConfigurationError, match="provider is required"):
        AuthSettings(provider="", issuer="iss", audience="aud")


def test_settings_unsupported_provider():
    with pytest.raises(AuthConfigurationError, match="Unsupported auth provider"):
        AuthSettings(provider="oauth", issuer="iss", audience="aud")


def test_settings_missing_issuer():
    with pytest.raises(AuthConfigurationError, match="issuer is required"):
        AuthSettings(provider="static", issuer="", audience="aud", public_key_path="p", jwt_key_id="k")


def test_settings_missing_audience():
    with pytest.raises(AuthConfigurationError, match="audience is required"):
        AuthSettings(provider="static", issuer="iss", audience="", public_key_path="p", jwt_key_id="k")


def test_settings_jwks_missing_url():
    with pytest.raises(AuthConfigurationError, match="jwks_url is required"):
        AuthSettings(provider="jwks", issuer="iss", audience="aud", jwks_url=None)


def test_settings_static_missing_path():
    with pytest.raises(AuthConfigurationError, match="public_key_path is required"):
        AuthSettings(provider="static", issuer="iss", audience="aud", public_key_path=None, jwt_key_id="k")


def test_settings_static_missing_kid():
    with pytest.raises(AuthConfigurationError, match="jwt_key_id is required"):
        AuthSettings(provider="static", issuer="iss", audience="aud", public_key_path="p", jwt_key_id=None)


def test_settings_from_env_valid_static():
    env = {
        "AUTH_PROVIDER": "static",
        "AUTH_ISSUER": "test-issuer",
        "AUTH_AUDIENCE": "test-aud",
        "AUTH_PUBLIC_KEY_PATH": "/tmp/pub.pem",
        "AUTH_JWT_KEY_ID": "key-1",
        "AUTH_LEEWAY_SECONDS": "45",
    }
    settings = AuthSettings.from_env(env)
    assert settings.provider == "static"
    assert settings.issuer == "test-issuer"
    assert settings.audience == "test-aud"
    assert settings.public_key_path == "/tmp/pub.pem"
    assert settings.jwt_key_id == "key-1"
    assert settings.leeway_seconds == 45


def test_settings_from_env_valid_jwks():
    env = {
        "AUTH_PROVIDER": "jwks",
        "AUTH_ISSUER": "test-issuer",
        "AUTH_AUDIENCE": "test-aud",
        "AUTH_JWKS_URL": "http://control-plane/.well-known/jwks.json",
    }
    settings = AuthSettings.from_env(env)
    assert settings.provider == "jwks"
    assert settings.jwks_url == "http://control-plane/.well-known/jwks.json"
    assert settings.leeway_seconds == 30
    assert settings.jwks_cache_ttl_seconds == 300


def test_settings_from_env_invalid_int():
    env = {
        "AUTH_PROVIDER": "static",
        "AUTH_ISSUER": "test-issuer",
        "AUTH_AUDIENCE": "test-aud",
        "AUTH_PUBLIC_KEY_PATH": "/tmp/pub.pem",
        "AUTH_JWT_KEY_ID": "key-1",
        "AUTH_LEEWAY_SECONDS": "not-an-int",
    }
    with pytest.raises(AuthConfigurationError, match="Invalid integer for AUTH_LEEWAY_SECONDS"):
        AuthSettings.from_env(env)


# ---------------------------------------------------------------------------
# 2. Factory and Caching Tests
# ---------------------------------------------------------------------------


def test_factory_static_key_missing_file():
    settings = AuthSettings(
        provider="static",
        issuer="iss",
        audience="aud",
        public_key_path="/nonexistent/path/file.pem",
        jwt_key_id="k",
    )
    with pytest.raises(AuthConfigurationError, match="Public key file not found"):
        build_token_verifier(settings)


def test_factory_static_key_empty_file():
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write("   \n")
        f.flush()
        f_path = f.name

    try:
        settings = AuthSettings(
            provider="static",
            issuer="iss",
            audience="aud",
            public_key_path=f_path,
            jwt_key_id="k",
        )
        with pytest.raises(AuthConfigurationError, match="Public key file is empty"):
            build_token_verifier(settings)
    finally:
        Path(f_path).unlink(missing_ok=True)


def test_factory_caches_verifier_and_reads_key_once(rsa_keypair, monkeypatch):
    reset_auth_cache()

    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write(rsa_keypair["public_pem"])
        f.flush()
        f_path = f.name

    try:
        monkeypatch.setenv("AUTH_PROVIDER", "static")
        monkeypatch.setenv("AUTH_ISSUER", "faultline-control-plane")
        monkeypatch.setenv("AUTH_AUDIENCE", "faultline")
        monkeypatch.setenv("AUTH_PUBLIC_KEY_PATH", f_path)
        monkeypatch.setenv("AUTH_JWT_KEY_ID", rsa_keypair["kid"])

        original_open = open
        read_count = 0

        def counting_open(file, *args, **kwargs):
            nonlocal read_count
            if str(file) == f_path:
                read_count += 1
            return original_open(file, *args, **kwargs)

        with patch("builtins.open", side_effect=counting_open):
            v1 = get_token_verifier()
            v2 = get_token_verifier()
            assert v1 is v2
            assert read_count == 1

        # Test reset_auth_cache
        reset_auth_cache()
        with patch("builtins.open", side_effect=counting_open):
            v3 = get_token_verifier()
            assert v3 is not v1
            assert read_count == 2
    finally:
        reset_auth_cache()
        Path(f_path).unlink(missing_ok=True)


def test_configure_auth_explicit():
    reset_auth_cache()
    settings = AuthSettings(
        provider="jwks",
        issuer="iss",
        audience="aud",
        jwks_url="http://control-plane/.well-known/jwks.json",
    )
    v1 = configure_auth(settings)
    v2 = get_token_verifier()
    assert v1 is v2
    reset_auth_cache()


# ---------------------------------------------------------------------------
# 3. Principal Tests
# ---------------------------------------------------------------------------


def test_principal_from_context_with_workspace():
    uid = uuid.uuid4()
    wid = uuid.uuid4()
    sid = uuid.uuid4()
    ctx = AuthContext(
        user_id=uid,
        workspace_id=wid,
        role="admin",
        session_id=sid,
        token_id="tok-1",
        expires_at=datetime.now(timezone.utc),
    )
    p = Principal.from_context(ctx)
    assert p.user_id == uid
    assert p.workspace_id == wid
    assert p.role == "admin"
    assert p.session_id == sid


def test_principal_from_context_without_workspace():
    uid = uuid.uuid4()
    ctx = AuthContext(
        user_id=uid,
        workspace_id=None,
        role="admin",
        session_id=None,
        token_id="tok-1",
        expires_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError, match="missing workspace_id"):
        Principal.from_context(ctx)


# ---------------------------------------------------------------------------
# 4. Error Policy Table & get_principal Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def test_app():
    app = FastAPI()

    @app.get("/test/principal")
    async def principal_endpoint(principal: Principal = Depends(get_principal)):
        return {
            "user_id": str(principal.user_id),
            "workspace_id": str(principal.workspace_id),
            "role": principal.role,
        }

    return app


@pytest.mark.asyncio
async def test_get_principal_missing_credentials(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # None
        res = await client.get("/test/principal")
        assert res.status_code == 401
        assert res.headers.get("www-authenticate") == "Bearer"
        assert res.json()["detail"] == "Missing or invalid credentials"

        # Non-Bearer scheme
        res = await client.get("/test/principal", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert res.status_code == 401
        assert res.headers.get("www-authenticate") == "Bearer"
        assert res.json()["detail"] == "Missing or invalid credentials"

        # Empty credentials
        res = await client.get("/test/principal", headers={"Authorization": "Bearer   "})
        assert res.status_code == 401
        assert res.headers.get("www-authenticate") == "Bearer"
        assert res.json()["detail"] == "Missing or invalid credentials"


@pytest.mark.asyncio
async def test_get_principal_invalid_token(test_app, rsa_keypair, monkeypatch):
    reset_auth_cache()
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline", leeway_seconds=0)

    # Monkeypatch get_token_verifier to return our verifier
    monkeypatch.setattr("faultline_auth.dependencies.get_token_verifier", lambda: verifier)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Expired token
        expired_token = make_test_jwt(
            rsa_keypair["private_key"],
            kid=rsa_keypair["kid"],
            workspace_id=uuid.uuid4(),
            exp_delta=timedelta(seconds=-10),
        )
        res = await client.get("/test/principal", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401
        assert res.headers.get("www-authenticate") == "Bearer"
        assert res.json()["detail"] == "Missing or invalid credentials"

        # Wrong issuer
        wrong_iss = make_test_jwt(
            rsa_keypair["private_key"],
            kid=rsa_keypair["kid"],
            workspace_id=uuid.uuid4(),
            issuer="wrong-issuer",
        )
        res = await client.get("/test/principal", headers={"Authorization": f"Bearer {wrong_iss}"})
        assert res.status_code == 401
        assert res.headers.get("www-authenticate") == "Bearer"
        assert res.json()["detail"] == "Missing or invalid credentials"

        # Unknown kid
        wrong_kid = make_test_jwt(
            rsa_keypair["private_key"],
            kid="unknown-kid",
            workspace_id=uuid.uuid4(),
        )
        res = await client.get("/test/principal", headers={"Authorization": f"Bearer {wrong_kid}"})
        assert res.status_code == 401
        assert res.headers.get("www-authenticate") == "Bearer"
        assert res.json()["detail"] == "Missing or invalid credentials"


@pytest.mark.asyncio
async def test_get_principal_invalid_workspace_claim(test_app, rsa_keypair, monkeypatch):
    reset_auth_cache()
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")
    monkeypatch.setattr("faultline_auth.dependencies.get_token_verifier", lambda: verifier)

    # Token with non-UUID workspace_id
    token = make_test_jwt(rsa_keypair["private_key"], kid=rsa_keypair["kid"], workspace_id="not-a-valid-uuid")

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get("/test/principal", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403
        assert res.json()["detail"] == "You do not have permission to access this resource"


@pytest.mark.asyncio
async def test_get_principal_keys_unavailable(test_app, monkeypatch):
    class FailingProvider:
        async def get_key(self, kid: str):
            raise KeysUnavailable("Remote JWKS endpoint down")

    verifier = TokenVerifier(FailingProvider(), issuer="faultline-control-plane", audience="faultline")
    monkeypatch.setattr("faultline_auth.dependencies.get_token_verifier", lambda: verifier)

    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImRldi0xIn0.eyJzdWIiOiIxIn0.c2ln"

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get("/test/principal", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 503
        assert res.json()["detail"] == "Authentication temporarily unavailable"


@pytest.mark.asyncio
async def test_get_principal_auth_config_error_at_request_time(test_app, monkeypatch):
    def bad_verifier():
        raise AuthConfigurationError("Configuration corrupted")

    monkeypatch.setattr("faultline_auth.dependencies.get_token_verifier", bad_verifier)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get("/test/principal", headers={"Authorization": "Bearer valid.token.structure"})
        assert res.status_code == 500
        assert res.json()["detail"] == "Internal server error"


@pytest.mark.asyncio
async def test_get_principal_missing_workspace_id(test_app, rsa_keypair, monkeypatch):
    reset_auth_cache()
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")
    monkeypatch.setattr("faultline_auth.dependencies.get_token_verifier", lambda: verifier)

    token = make_test_jwt(rsa_keypair["private_key"], kid=rsa_keypair["kid"], workspace_id=None)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get("/test/principal", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403
        assert res.json()["detail"] == "You do not have permission to access this resource"


@pytest.mark.asyncio
async def test_get_principal_success(test_app, rsa_keypair, monkeypatch):
    reset_auth_cache()
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")
    monkeypatch.setattr("faultline_auth.dependencies.get_token_verifier", lambda: verifier)

    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    token = make_test_jwt(
        rsa_keypair["private_key"],
        kid=rsa_keypair["kid"],
        sub=user_id,
        workspace_id=workspace_id,
        role="owner",
    )

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get("/test/principal", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == str(user_id)
        assert data["workspace_id"] == str(workspace_id)
        assert data["role"] == "owner"


# ---------------------------------------------------------------------------
# 5. AuthDependencies.current_user Does Not Leak Exception Text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_current_user_no_exception_leak(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline", leeway_seconds=0)
    deps = AuthDependencies(verifier)
    app = FastAPI()

    @app.get("/test/user")
    async def user_endpoint(ctx: AuthContext = Depends(deps.current_user())):
        return {"user_id": str(ctx.user_id)}

    expired_token = make_test_jwt(
        rsa_keypair["private_key"],
        kid=rsa_keypair["kid"],
        workspace_id=uuid.uuid4(),
        exp_delta=timedelta(seconds=-10),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/test/user", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401
        assert res.headers.get("www-authenticate") == "Bearer"
        assert res.json()["detail"] == "Missing or invalid credentials"
        assert "Signature verification failed" not in res.text
        assert "Token is expired" not in res.text
        assert "exp" not in res.text

