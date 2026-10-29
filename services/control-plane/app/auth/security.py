import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings


class AuthError(Exception):
    """Base exception for authentication and authorization errors."""


class EmailAlreadyRegistered(AuthError):
    """Raised when attempting to sign up with an email that is already registered."""


class InvalidCredentials(AuthError):
    """Raised when authentication credentials (email/password) are invalid or user inactive."""


class InvalidToken(AuthError):
    """Raised when a JWT is missing, expired, tampered with, or otherwise invalid."""


password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH: str = password_hasher.hash(
    "faultline-dummy-password-for-timing-mitigation"
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return password_hasher.verify(hashed_password, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy_password(password: str) -> bool:
    """Run password verification against a dummy hash to mitigate timing attacks."""
    try:
        return password_hasher.verify(DUMMY_PASSWORD_HASH, password)
    except Exception:
        return False


def create_access_token(
    user_id: uuid.UUID | str,
    workspaces: list[dict[str, Any]] | None = None,
    ttl: timedelta | None = None,
    now: datetime | None = None,
    private_key: str | None = None,
    key_id: str | None = None,
    issuer: str | None = None,
    audience: str | None = None,
) -> str:
    """Create an RS256-signed JWT access token.
    Claims: iss, aud, sub, iat, exp, jti, workspaces.
    Does NOT contain email, password hash, or secrets.
    """
    if private_key is None:
        private_key = settings.get_jwt_private_key()
    if key_id is None:
        key_id = settings.jwt_key_id
    if issuer is None:
        issuer = settings.jwt_issuer
    if audience is None:
        audience = settings.jwt_audience
    if ttl is None:
        ttl = timedelta(minutes=settings.access_token_ttl_minutes)
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    exp = now + ttl
    payload: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
        "workspaces": workspaces if workspaces is not None else [],
    }
    headers = {"kid": key_id}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


def decode_access_token(
    token: str,
    public_key: str | None = None,
    issuer: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """Decode and validate an RS256 JWT access token.
    Enforces algorithm RS256 only, verifies signature, exp, iss, and aud,
    and requires claims: sub, exp, iat, iss, aud.
    """
    if public_key is None:
        public_key = settings.get_jwt_public_key()
    if issuer is None:
        issuer = settings.jwt_issuer
    if audience is None:
        audience = settings.jwt_audience

    try:
        return jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
                "require": ["sub", "exp", "iat", "iss", "aud"],
            },
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(f"Token validation failed: {exc}") from exc

