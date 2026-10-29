import uuid
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from faultline_auth import StaticKeyProvider, TokenVerifier
from faultline_auth.errors import InvalidToken

from app.auth.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    verify_dummy_password,
    verify_password,
)
from app.core.config import settings


def test_hash_and_verify() -> None:
    password = "CorrectHorseBatteryStaple123"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True


def test_wrong_password() -> None:
    password = "CorrectHorseBatteryStaple123"
    hashed = hash_password(password)

    assert verify_password("WrongPassword123", hashed) is False
    assert verify_dummy_password("AnyPassword") is False


def test_hash_refresh_token() -> None:
    token = "some-random-refresh-token"
    h1 = hash_refresh_token(token)
    h2 = hash_refresh_token(token)
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_token_round_trip(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    session_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(
        user_id=user_id,
        workspace_id=workspace_id,
        role="owner",
        sid=session_id,
        private_key=priv_pem,
    )

    verifier = TokenVerifier(
        StaticKeyProvider(pub_pem, settings.jwt_key_id),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    ctx = await verifier.verify(token)

    assert ctx.user_id == user_id
    assert ctx.workspace_id == workspace_id
    assert ctx.role == "owner"
    assert ctx.session_id == session_id
    assert ctx.token_id is not None


@pytest.mark.asyncio
async def test_expired_token(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(
        user_id=user_id,
        ttl=timedelta(seconds=-10),
        private_key=priv_pem,
    )

    verifier = TokenVerifier(
        StaticKeyProvider(pub_pem, settings.jwt_key_id),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        leeway_seconds=0,
    )
    with pytest.raises(InvalidToken, match="Signature has expired"):
        await verifier.verify(token)


@pytest.mark.asyncio
async def test_wrong_audience(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(
        user_id=user_id,
        audience="wrong-audience",
        private_key=priv_pem,
    )

    verifier = TokenVerifier(
        StaticKeyProvider(pub_pem, settings.jwt_key_id),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    with pytest.raises(InvalidToken, match="Audience doesn't match"):
        await verifier.verify(token)


@pytest.mark.asyncio
async def test_wrong_issuer(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(
        user_id=user_id,
        issuer="wrong-issuer",
        private_key=priv_pem,
    )

    verifier = TokenVerifier(
        StaticKeyProvider(pub_pem, settings.jwt_key_id),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    with pytest.raises(InvalidToken, match="Invalid issuer"):
        await verifier.verify(token)


@pytest.mark.asyncio
async def test_tampered_signature(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(user_id=user_id, private_key=priv_pem)
    header, payload, signature = token.split(".")

    tampered_sig = ("A" if signature[0] != "A" else "B") + signature[1:]
    tampered_token = f"{header}.{payload}.{tampered_sig}"

    verifier = TokenVerifier(
        StaticKeyProvider(pub_pem, settings.jwt_key_id),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    with pytest.raises(InvalidToken, match="Signature verification failed"):
        await verifier.verify(tampered_token)


@pytest.mark.asyncio
async def test_token_signed_with_another_key(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    _, pub_pem, _, _ = test_keys

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_priv_pem = other_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    token = create_access_token(user_id=user_id, private_key=other_priv_pem)

    verifier = TokenVerifier(
        StaticKeyProvider(pub_pem, settings.jwt_key_id),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    with pytest.raises(InvalidToken, match="Signature verification failed"):
        await verifier.verify(token)
