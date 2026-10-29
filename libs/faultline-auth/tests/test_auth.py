import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from faultline_auth import (
    AuthContext,
    AuthDependencies,
    InvalidToken,
    JwksKeyProvider,
    KeysUnavailable,
    StaticKeyProvider,
    TokenVerifier,
)


def make_token(
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


# 1. Valid token
@pytest.mark.asyncio
async def test_valid_token(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")

    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    session_id = uuid.uuid4()
    token = make_token(
        rsa_keypair["private_key"],
        kid=rsa_keypair["kid"],
        sub=str(user_id),
        workspace_id=workspace_id,
        role="admin",
        sid=session_id,
    )

    ctx = await verifier.verify(token)
    assert ctx.user_id == user_id
    assert ctx.workspace_id == workspace_id
    assert ctx.role == "admin"
    assert ctx.session_id == session_id
    assert ctx.token_id is not None
    assert ctx.expires_at > datetime.now(timezone.utc)


# 2. Expired token
@pytest.mark.asyncio
async def test_expired_token(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline", leeway_seconds=0)

    token = make_token(
        rsa_keypair["private_key"],
        kid=rsa_keypair["kid"],
        exp_delta=timedelta(seconds=-10),
    )
    with pytest.raises(InvalidToken, match="Signature has expired"):
        await verifier.verify(token)


# 3. Wrong audience
@pytest.mark.asyncio
async def test_wrong_audience(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")

    token = make_token(
        rsa_keypair["private_key"],
        kid=rsa_keypair["kid"],
        audience="wrong-aud",
    )
    with pytest.raises(InvalidToken, match="Audience doesn't match"):
        await verifier.verify(token)


# 4. Wrong issuer
@pytest.mark.asyncio
async def test_wrong_issuer(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")

    token = make_token(
        rsa_keypair["private_key"],
        kid=rsa_keypair["kid"],
        issuer="wrong-issuer",
    )
    with pytest.raises(InvalidToken, match="Invalid issuer"):
        await verifier.verify(token)


# 5. Tampered signature
@pytest.mark.asyncio
async def test_tampered_signature(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")

    token = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"])
    parts = token.split(".")
    tampered_sig = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    with pytest.raises(InvalidToken, match="Signature verification failed"):
        await verifier.verify(tampered_token)


# 6. Token signed by unknown key
@pytest.mark.asyncio
async def test_token_signed_by_unknown_key(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")

    token = make_token(rsa_keypair["private_key"], kid="unknown-kid")
    with pytest.raises(InvalidToken, match="Unknown key ID"):
        await verifier.verify(token)


# 7. HS256-forged token using public key as secret
@pytest.mark.asyncio
async def test_hs256_forged_token(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")

    # Attacker signs token using HMAC-SHA256 with an arbitrary symmetric secret
    forged_token = make_token(
        key="symmetric-secret-key-at-least-32-bytes-long",
        kid=rsa_keypair["kid"],
        alg="HS256",
    )
    with pytest.raises(InvalidToken, match="Unsupported algorithm 'HS256'"):
        await verifier.verify(forged_token)


# 8. Refresh-type token rejected
@pytest.mark.asyncio
async def test_refresh_token_rejected(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")

    token = make_token(
        rsa_keypair["private_key"],
        kid=rsa_keypair["kid"],
        token_type="refresh",
    )
    with pytest.raises(InvalidToken, match="must be 'access'"):
        await verifier.verify(token)


# 9. Missing required claim
@pytest.mark.asyncio
async def test_missing_required_claim(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")

    token = make_token(
        rsa_keypair["private_key"],
        kid=rsa_keypair["kid"],
        omit_claims=["jti"],
    )
    with pytest.raises(InvalidToken, match='missing the "jti" claim'):
        await verifier.verify(token)


# 10. Unknown kid triggers exactly one refetch and respects cooldown
@pytest.mark.asyncio
async def test_unknown_kid_refetch_and_cooldown(rsa_keypair):
    fetch_count = 0

    def handler(request):
        nonlocal fetch_count
        fetch_count += 1
        return httpx.Response(200, json=rsa_keypair["jwks"])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = JwksKeyProvider(
            "https://control.internal/.well-known/jwks.json",
            refetch_cooldown_seconds=10,
            client=client,
        )
        verifier = TokenVerifier(provider, issuer="faultline-control-plane", audience="faultline")

        # Initial fetch happens when token with valid kid is verified
        token1 = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"])
        await verifier.verify(token1)
        assert fetch_count == 1

        # Simulate time passing past the cooldown
        provider._last_fetch_attempt_at = time.monotonic() - 15

        # Token with unknown kid triggers refetch
        token_unknown1 = make_token(rsa_keypair["private_key"], kid="unknown-1")
        with pytest.raises(InvalidToken, match="not found in JWKS"):
            await verifier.verify(token_unknown1)
        assert fetch_count == 2

        # Second token with unknown kid within cooldown does NOT trigger fetch
        token_unknown2 = make_token(rsa_keypair["private_key"], kid="unknown-2")
        with pytest.raises(InvalidToken, match="not found in cached JWKS"):
            await verifier.verify(token_unknown2)
        assert fetch_count == 2


# 11. JWKS down but keys cached still verifies
@pytest.mark.asyncio
async def test_jwks_down_keys_cached_still_verifies(rsa_keypair):
    should_fail = False

    def handler(request):
        if should_fail:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json=rsa_keypair["jwks"])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = JwksKeyProvider(
            "https://control.internal/.well-known/jwks.json",
            cache_ttl_seconds=0,  # Expire immediately
            client=client,
        )
        verifier = TokenVerifier(provider, issuer="faultline-control-plane", audience="faultline")

        token = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"])
        # First verify succeeds and caches keys
        await verifier.verify(token)

        # Now JWKS goes down
        should_fail = True
        # Verify still succeeds using cached keys
        ctx = await verifier.verify(token)
        assert ctx is not None


# 12. JWKS down with no cache raises KeysUnavailable (503 via dependency)
@pytest.mark.asyncio
async def test_jwks_down_no_cache_keys_unavailable(rsa_keypair):
    def handler(request):
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = JwksKeyProvider(
            "https://control.internal/.well-known/jwks.json",
            client=client,
        )
        verifier = TokenVerifier(provider, issuer="faultline-control-plane", audience="faultline")

        token = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"])
        with pytest.raises(KeysUnavailable):
            await verifier.verify(token)

        # Test 503 via FastAPI dependency
        deps = AuthDependencies(verifier)
        app = FastAPI()

        @app.get("/test")
        async def endpoint(user: AuthContext = Depends(deps.current_user())):
            return {"user_id": str(user.user_id)}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
            res = await test_client.get("/test", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 503
            assert res.json()["detail"] == "Authentication temporarily unavailable"


# 13. No token -> 401 with WWW-Authenticate header
@pytest.mark.asyncio
async def test_no_token_returns_401(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")
    deps = AuthDependencies(verifier)
    app = FastAPI()

    @app.get("/protected")
    async def protected(user: AuthContext = Depends(deps.current_user())):
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/protected")
        assert res.status_code == 401
        assert res.headers.get("www-authenticate") == "Bearer"


# 14. require_workspace mismatch -> 404
@pytest.mark.asyncio
async def test_require_workspace_mismatch_returns_404(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")
    deps = AuthDependencies(verifier)
    app = FastAPI()

    @app.get("/workspaces/{workspace_id}")
    async def get_workspace(ctx: AuthContext = Depends(deps.require_workspace())):
        return {"workspace_id": str(ctx.workspace_id)}

    actual_ws = uuid.uuid4()
    different_ws = uuid.uuid4()
    token_with_ws = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"], workspace_id=actual_ws)
    token_without_ws = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"], workspace_id=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Match -> 200
        res = await client.get(
            f"/workspaces/{actual_ws}",
            headers={"Authorization": f"Bearer {token_with_ws}"},
        )
        assert res.status_code == 200
        assert res.json()["workspace_id"] == str(actual_ws)

        # Mismatch -> 404 (never 403)
        res = await client.get(
            f"/workspaces/{different_ws}",
            headers={"Authorization": f"Bearer {token_with_ws}"},
        )
        assert res.status_code == 404
        assert res.json()["detail"] == "Workspace not found"

        # No workspace in token -> 404
        res = await client.get(
            f"/workspaces/{actual_ws}",
            headers={"Authorization": f"Bearer {token_without_ws}"},
        )
        assert res.status_code == 404


# 15. require_role too low -> 403 and sufficient -> OK
@pytest.mark.asyncio
async def test_require_role_enforcement(rsa_keypair):
    kp = StaticKeyProvider(rsa_keypair["public_pem"], rsa_keypair["kid"])
    verifier = TokenVerifier(kp, issuer="faultline-control-plane", audience="faultline")
    deps = AuthDependencies(verifier)
    app = FastAPI()

    @app.delete("/workspaces/{workspace_id}/danger")
    async def danger(ctx: AuthContext = Depends(deps.require_role("admin"))):
        return {"status": "success"}

    ws_id = uuid.uuid4()
    viewer_token = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"], workspace_id=ws_id, role="viewer")
    admin_token = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"], workspace_id=ws_id, role="admin")
    owner_token = make_token(rsa_keypair["private_key"], kid=rsa_keypair["kid"], workspace_id=ws_id, role="owner")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # viewer is lower than admin -> 403
        res = await client.delete(
            f"/workspaces/{ws_id}/danger",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 403
        assert res.json()["detail"] == "Insufficient permissions"

        # admin is equal to min_role -> 200
        res = await client.delete(
            f"/workspaces/{ws_id}/danger",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200

        # owner is higher than admin -> 200
        res = await client.delete(
            f"/workspaces/{ws_id}/danger",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert res.status_code == 200
