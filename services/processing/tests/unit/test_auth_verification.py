import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from faultline_auth import (
    AuthConfigurationError,
    Principal,
    configure_auth,
    get_principal,
    get_token_verifier,
    reset_auth_cache,
)


def make_test_token(
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
    omit_claims=None,
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

    if omit_claims:
        for c in omit_claims:
            payload.pop(c, None)

    headers = {"kid": kid}
    return jwt.encode(payload, key, algorithm=alg, headers=headers)


@pytest.fixture(autouse=True)
def configure_auth_settings(rsa_keys, monkeypatch):
    reset_auth_cache()
    monkeypatch.setenv("AUTH_PROVIDER", "static")
    monkeypatch.setenv("AUTH_ISSUER", "faultline-control-plane")
    monkeypatch.setenv("AUTH_AUDIENCE", "faultline")
    monkeypatch.setenv("AUTH_LEEWAY_SECONDS", "30")
    monkeypatch.setenv("AUTH_PUBLIC_KEY_PATH", rsa_keys["pub_key_path"])
    monkeypatch.setenv("AUTH_JWT_KEY_ID", rsa_keys["kid"])
    yield
    reset_auth_cache()


# 1. Valid token returns correct Principal
@pytest.mark.asyncio
async def test_valid_token_returns_principal(rsa_keys):
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    token = make_test_token(
        rsa_keys["private_key"],
        kid=rsa_keys["kid"],
        sub=str(user_id),
        workspace_id=workspace_id,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    principal = await get_principal(creds)

    assert isinstance(principal, Principal)
    assert principal.user_id == user_id
    assert principal.workspace_id == workspace_id


# 2. Missing credentials (None) returns 401
@pytest.mark.asyncio
async def test_missing_credentials_returns_401():
    with pytest.raises(HTTPException) as exc_info:
        await get_principal(None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"
    assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"


# 3. Wrong scheme returns 401
@pytest.mark.asyncio
async def test_wrong_scheme_returns_401(rsa_keys):
    token = make_test_token(rsa_keys["private_key"], workspace_id=uuid.uuid4())
    creds = HTTPAuthorizationCredentials(scheme="Basic", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 4. Empty token returns 401
@pytest.mark.asyncio
async def test_empty_token_returns_401():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 5. Malformed token returns 401
@pytest.mark.asyncio
async def test_malformed_token_returns_401():
    for bad in ["not-a-jwt", "abc.def", "eyJhbGci.invalid"]:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=bad)
        with pytest.raises(HTTPException) as exc_info:
            await get_principal(creds)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Missing or invalid credentials"


# 6. Bad signature (different RSA private key) returns 401
@pytest.mark.asyncio
async def test_bad_signature_returns_401(rsa_keys):
    from cryptography.hazmat.primitives.asymmetric import rsa

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_test_token(other_key, kid=rsa_keys["kid"], workspace_id=uuid.uuid4())
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 7. Expired token returns 401
@pytest.mark.asyncio
async def test_expired_token_returns_401(rsa_keys, monkeypatch):
    monkeypatch.setenv("AUTH_LEEWAY_SECONDS", "0")
    reset_auth_cache()
    token = make_test_token(
        rsa_keys["private_key"],
        kid=rsa_keys["kid"],
        workspace_id=uuid.uuid4(),
        exp_delta=timedelta(seconds=-10),
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 8. Wrong issuer returns 401
@pytest.mark.asyncio
async def test_wrong_issuer_returns_401(rsa_keys):
    token = make_test_token(
        rsa_keys["private_key"],
        kid=rsa_keys["kid"],
        workspace_id=uuid.uuid4(),
        issuer="wrong-issuer",
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 9. Wrong audience returns 401
@pytest.mark.asyncio
async def test_wrong_audience_returns_401(rsa_keys):
    token = make_test_token(
        rsa_keys["private_key"],
        kid=rsa_keys["kid"],
        workspace_id=uuid.uuid4(),
        audience="wrong-audience",
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 10. Algorithm none returns 401
@pytest.mark.asyncio
async def test_algorithm_none_rejected(rsa_keys):
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "faultline-control-plane",
        "aud": "faultline",
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "jti": str(uuid.uuid4()),
        "workspace_id": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, key="", algorithm="none", headers={"kid": rsa_keys["kid"]})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 11. HS256 signed with public key PEM as secret returns 401
@pytest.mark.asyncio
async def test_hs256_confusion_rejected(rsa_keys):
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "faultline-control-plane",
        "aud": "faultline",
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "jti": str(uuid.uuid4()),
        "workspace_id": str(uuid.uuid4()),
    }
    header_json = json.dumps({"alg": "HS256", "kid": rsa_keys["kid"]}).encode()
    payload_json = json.dumps(payload).encode()
    h_b64 = base64.urlsafe_b64encode(header_json).rstrip(b"=").decode()
    p_b64 = base64.urlsafe_b64encode(payload_json).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(
        hmac.new(rsa_keys["public_pem"].encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    token = f"{h_b64}.{p_b64}.{sig}"

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 12. Unknown kid returns 401
@pytest.mark.asyncio
async def test_unknown_kid_returns_401(rsa_keys):
    token = make_test_token(rsa_keys["private_key"], kid="unknown-kid", workspace_id=uuid.uuid4())
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 13. Missing subject claim returns 401
@pytest.mark.asyncio
async def test_missing_subject_returns_401(rsa_keys):
    token = make_test_token(
        rsa_keys["private_key"],
        kid=rsa_keys["kid"],
        workspace_id=uuid.uuid4(),
        omit_claims=["sub"],
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 14. Non-UUID subject claim returns 401
@pytest.mark.asyncio
async def test_non_uuid_subject_returns_401(rsa_keys):
    token = make_test_token(
        rsa_keys["private_key"],
        kid=rsa_keys["kid"],
        sub="not-a-valid-uuid",
        workspace_id=uuid.uuid4(),
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"


# 15. Missing workspace_id claim returns 403
@pytest.mark.asyncio
async def test_missing_workspace_id_returns_403(rsa_keys):
    token = make_test_token(
        rsa_keys["private_key"],
        kid=rsa_keys["kid"],
        workspace_id=None,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You do not have permission to access this resource"


# 16. Non-UUID workspace_id claim returns 403
@pytest.mark.asyncio
async def test_non_uuid_workspace_id_returns_403(rsa_keys):
    token = make_test_token(
        rsa_keys["private_key"],
        kid=rsa_keys["kid"],
        workspace_id="invalid-uuid-string",
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You do not have permission to access this resource"


# 17. Misconfiguration at request time returns 500 and logs ERROR
@pytest.mark.asyncio
async def test_misconfiguration_missing_key_file(rsa_keys, monkeypatch, caplog):
    monkeypatch.setenv("AUTH_PUBLIC_KEY_PATH", "/nonexistent/path/public.pem")
    reset_auth_cache()

    token = make_test_token(rsa_keys["private_key"], workspace_id=uuid.uuid4())
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"
    assert any("Authentication configuration error" in record.message for record in caplog.records)


# 18. JWKS provider: valid token verified through JWKS
@pytest.mark.asyncio
async def test_jwks_provider_valid_token(rsa_keys, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "jwks")
    monkeypatch.setenv("AUTH_JWKS_URL", "http://test-control/.well-known/jwks.json")
    reset_auth_cache()

    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    token = make_test_token(
        rsa_keys["private_key"],
        kid="dev-1",
        sub=str(user_id),
        workspace_id=workspace_id,
    )

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=rsa_keys["jwks"]))
    async with httpx.AsyncClient(transport=transport) as mock_client:
        verifier = get_token_verifier()
        verifier.key_provider._client = mock_client

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        principal = await get_principal(creds)

        assert principal.user_id == user_id
        assert principal.workspace_id == workspace_id


# 19. JWKS provider: cache hit within TTL avoids repeat HTTP calls
@pytest.mark.asyncio
async def test_jwks_provider_cache_hit(rsa_keys, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "jwks")
    monkeypatch.setenv("AUTH_JWKS_URL", "http://test-control/.well-known/jwks.json")
    reset_auth_cache()

    call_count = 0

    def jwks_handler(req):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=rsa_keys["jwks"])

    transport = httpx.MockTransport(jwks_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        verifier = get_token_verifier()
        verifier.key_provider._client = mock_client

        token = make_test_token(rsa_keys["private_key"], kid="dev-1", workspace_id=uuid.uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        p1 = await get_principal(creds)
        p2 = await get_principal(creds)

        assert p1 is not None
        assert p2 is not None
        assert call_count == 1  # Only 1 HTTP call made


# 20. JWKS provider: stale cache used when JWKS fetch fails
@pytest.mark.asyncio
async def test_jwks_provider_stale_cache_on_fetch_failure(rsa_keys, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "jwks")
    monkeypatch.setenv("AUTH_JWKS_URL", "http://test-control/.well-known/jwks.json")
    monkeypatch.setenv("AUTH_JWKS_CACHE_TTL_SECONDS", "0")  # Expire immediately
    reset_auth_cache()

    should_fail = False

    def jwks_handler(req):
        if should_fail:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json=rsa_keys["jwks"])

    transport = httpx.MockTransport(jwks_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        verifier = get_token_verifier()
        verifier.key_provider._client = mock_client

        token = make_test_token(rsa_keys["private_key"], kid="dev-1", workspace_id=uuid.uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Initial fetch succeeds and populates cache
        p1 = await get_principal(creds)
        assert p1 is not None

        # JWKS now fails, but cached key is used
        should_fail = True
        p2 = await get_principal(creds)
        assert p2 is not None


# 21. JWKS provider: empty cache and fetch fails returns 503 and logs ERROR
@pytest.mark.asyncio
async def test_jwks_provider_empty_cache_fetch_fails_returns_503(rsa_keys, monkeypatch, caplog):
    monkeypatch.setenv("AUTH_PROVIDER", "jwks")
    monkeypatch.setenv("AUTH_JWKS_URL", "http://test-control/.well-known/jwks.json")
    reset_auth_cache()

    transport = httpx.MockTransport(lambda req: httpx.Response(503, text="Service Unavailable"))
    async with httpx.AsyncClient(transport=transport) as mock_client:
        verifier = get_token_verifier()
        verifier.key_provider._client = mock_client

        token = make_test_token(rsa_keys["private_key"], kid="dev-1", workspace_id=uuid.uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_principal(creds)
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Authentication temporarily unavailable"
        assert any("Authentication keys unavailable" in r.message for r in caplog.records)


# 22. Fast-fail at startup on misconfiguration
def test_configure_auth_fails_fast_on_invalid_env(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "invalid_provider")
    reset_auth_cache()
    with pytest.raises(AuthConfigurationError, match="Unsupported auth provider"):
        configure_auth()
