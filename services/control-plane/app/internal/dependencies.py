import hmac
import logging
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

INTERNAL_SERVICE_TOKEN_HEADER = "X-Service-Token"


async def verify_internal_service_secret(
    x_service_token: Annotated[
        str | None, Header(alias=INTERNAL_SERVICE_TOKEN_HEADER)
    ] = None,
) -> None:
    """Validate internal service-to-service credential.

    Rejects requests with HTTP 401 if the configured secret is empty,
    if the incoming header is missing, or if the token does not match.
    Uses constant-time comparison to prevent timing side-channel attacks.
    """
    expected_secret = settings.internal_service_secret
    if not expected_secret:
        logger.error(
            "Internal service secret is not configured on the Control Plane."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid service token",
        )

    if not x_service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid service token",
        )

    if not hmac.compare_digest(x_service_token, expected_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid service token",
        )

