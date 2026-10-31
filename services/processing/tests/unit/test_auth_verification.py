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

from app.core.auth import Principal, get_jwks_provider, get_principal, reset_jwks_provider
from app.core.config import settings


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
    monkeypatch.setattr(settings, "auth_provider", "static")
    monkeypatch.setattr(settings, "auth_issuer", "faultline-control-plane")
    monkeypatch.setattr(settings, "auth_audience", "faultline")
    monkeypatch.setattr(settings, "auth_leeway_seconds", 30)
    monkeypatch.setattr(settings, "auth_public_key_path", rsa_keys["pub_key_path"])
    monkeypatch.setattr(settings, "auth_jwt_key_id", rsa_keys["kid"])


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
    monkeypatch.setattr(settings, "auth_leeway_seconds", 0)
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


# 17. Misconfiguration: missing or unreadable key file returns 401 and logs ERROR
@pytest.mark.asyncio
async def test_misconfiguration_missing_key_file(rsa_keys, monkeypatch, caplog):
    monkeypatch.setattr(settings, "auth_public_key_path", "/nonexistent/path/public.pem")

    token = make_test_token(rsa_keys["private_key"], workspace_id=uuid.uuid4())
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_principal(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid credentials"
    assert any("Authentication configuration error" in record.message for record in caplog.records)


# 18. JWKS provider: valid token verified through JWKS
@pytest.mark.asyncio
async def test_jwks_provider_valid_token(rsa_keys, monkeypatch):
    reset_jwks_provider()
    monkeypatch.setattr(settings, "auth_provider", "jwks")
    monkeypatch.setattr(settings, "auth_jwks_url", "http://test-control/.well-known/jwks.json")

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
        provider = get_jwks_provider()
        provider._client = mock_client

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        principal = await get_principal(creds)

        assert principal.user_id == user_id
        assert principal.workspace_id == workspace_id


# 19. JWKS provider: cache hit within TTL avoids repeat HTTP calls
@pytest.mark.asyncio
async def test_jwks_provider_cache_hit(rsa_keys, monkeypatch):
    reset_jwks_provider()
    monkeypatch.setattr(settings, "auth_provider", "jwks")
    monkeypatch.setattr(settings, "auth_jwks_url", "http://test-control/.well-known/jwks.json")

    call_count = 0

    def jwks_handler(req):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=rsa_keys["jwks"])

    transport = httpx.MockTransport(jwks_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        provider = get_jwks_provider()
        provider._client = mock_client

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
    reset_jwks_provider()
    monkeypatch.setattr(settings, "auth_provider", "jwks")
    monkeypatch.setattr(settings, "auth_jwks_url", "http://test-control/.well-known/jwks.json")
    monkeypatch.setattr(settings, "auth_jwks_cache_ttl_seconds", 0)  # Expire immediately

    should_fail = False

    def jwks_handler(req):
        if should_fail:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json=rsa_keys["jwks"])

    transport = httpx.MockTransport(jwks_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        provider = get_jwks_provider()
        provider._client = mock_client

        token = make_test_token(rsa_keys["private_key"], kid="dev-1", workspace_id=uuid.uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Initial fetch succeeds and populates cache
        p1 = await get_principal(creds)
        assert p1 is not None

        # JWKS now fails, but cached key is used
        should_fail = True
        p2 = await get_principal(creds)
        assert p2 is not None


# 21. JWKS provider: empty cache and fetch fails returns 401 and logs ERROR
@pytest.mark.asyncio
async def test_jwks_provider_empty_cache_fetch_fails_returns_401(rsa_keys, monkeypatch, caplog):
    reset_jwks_provider()
    monkeypatch.setattr(settings, "auth_provider", "jwks")
    monkeypatch.setattr(settings, "auth_jwks_url", "http://test-control/.well-known/jwks.json")

    transport = httpx.MockTransport(lambda req: httpx.Response(503, text="Service Unavailable"))
    async with httpx.AsyncClient(transport=transport) as mock_client:
        provider = get_jwks_provider()
        provider._client = mock_client

        token = make_test_token(rsa_keys["private_key"], kid="dev-1", workspace_id=uuid.uuid4())
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_principal(creds)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Missing or invalid credentials"
        assert any("Authentication keys unavailable" in r.message for r in caplog.records)
