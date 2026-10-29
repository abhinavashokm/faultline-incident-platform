import hashlib
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


class InvalidRefreshToken(AuthError):
    """Raised when a refresh token is invalid, expired, revoked, or user inactive."""


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


def hash_refresh_token(token: str) -> str:
    """Compute the SHA-256 hex digest of a refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: uuid.UUID | str,
    *,
    workspace_id: uuid.UUID | str | None = None,
    role: str | None = None,
    sid: uuid.UUID | str | None = None,
    ttl: timedelta | None = None,
    now: datetime | None = None,
    private_key: str | None = None,
    key_id: str | None = None,
    issuer: str | None = None,
    audience: str | None = None,
) -> str:
    """Create an RS256-signed JWT access token.
    Claims: iss, aud, sub, type ('access'), jti, iat, exp,
    and optionally workspace_id, role, sid.
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
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if workspace_id is not None:
        payload["workspace_id"] = str(workspace_id)
    if role is not None:
        payload["role"] = role
    if sid is not None:
        payload["sid"] = str(sid)

    headers = {"kid": key_id}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)
