import uuid
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.security import (
    InvalidToken,
    create_access_token,
    decode_access_token,
    hash_password,
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


def test_token_round_trip(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(
        user_id=user_id,
        workspaces=[],
        private_key=priv_pem,
    )
    payload = decode_access_token(token, public_key=pub_pem)

    assert payload["sub"] == str(user_id)
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience
    assert payload["workspaces"] == []
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


def test_expired_token(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    # Token with negative TTL is already expired
    token = create_access_token(
        user_id=user_id,
        ttl=timedelta(seconds=-10),
        private_key=priv_pem,
    )

    with pytest.raises(InvalidToken, match="Token validation failed"):
        decode_access_token(token, public_key=pub_pem)


def test_wrong_audience(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(
        user_id=user_id,
        audience="wrong-audience",
        private_key=priv_pem,
    )

    with pytest.raises(InvalidToken, match="Token validation failed"):
        decode_access_token(token, public_key=pub_pem, audience="expected-audience")


def test_wrong_issuer(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(
        user_id=user_id,
        issuer="wrong-issuer",
        private_key=priv_pem,
    )

    with pytest.raises(InvalidToken, match="Token validation failed"):
        decode_access_token(token, public_key=pub_pem, issuer="expected-issuer")


def test_tampered_signature(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    priv_pem, pub_pem, _, _ = test_keys

    token = create_access_token(user_id=user_id, private_key=priv_pem)
    header, payload, signature = token.split(".")

    # Tamper with signature
    tampered_sig = ("A" if signature[0] != "A" else "B") + signature[1:]
    tampered_token = f"{header}.{payload}.{tampered_sig}"

    with pytest.raises(InvalidToken, match="Token validation failed"):
        decode_access_token(tampered_token, public_key=pub_pem)


def test_token_signed_with_another_key(test_keys: tuple[str, str, ...]) -> None:
    user_id = uuid.uuid4()
    _, pub_pem, _, _ = test_keys

    # Generate an independent second RSA keypair
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_priv_pem = other_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    token = create_access_token(user_id=user_id, private_key=other_priv_pem)

    with pytest.raises(InvalidToken, match="Token validation failed"):
        decode_access_token(token, public_key=pub_pem)

