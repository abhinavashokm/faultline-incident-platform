import hashlib
import hmac
import secrets
import uuid

from app.core.config import settings


def generate_otp() -> str:
    """Generate a 6-digit numeric verification code using secrets.randbelow.
    Never log or store the raw code.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(
    user_id: uuid.UUID | str,
    code: str,
    secret: str | None = None,
) -> str:
    """Compute HMAC-SHA256 hex digest over f"{user_id}:{code}" using OTP_HMAC_SECRET.
    Never log or store the raw code.
    """
    if secret is None:
        secret = settings.otp_hmac_secret
    message = f"{user_id}:{code}".encode("utf-8")
    return hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def verify_otp(
    user_id: uuid.UUID | str,
    code: str,
    expected_hash: str,
    secret: str | None = None,
) -> bool:
    """Verify an OTP code against an expected HMAC-SHA256 hash using constant-time comparison."""
    computed_hash = hash_otp(user_id, code, secret=secret)
    return hmac.compare_digest(computed_hash, expected_hash)

