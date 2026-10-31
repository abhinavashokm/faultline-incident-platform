import logging
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from faultline_auth import (
    AuthContext,
    InvalidToken,
    InvalidWorkspaceClaim,
    JwksKeyProvider,
    KeyProvider,
    KeysUnavailable,
    StaticKeyProvider,
    TokenVerifier,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

http_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    workspace_id: UUID


_jwks_provider: JwksKeyProvider | None = None
_jwks_provider_url: str | None = None


def reset_jwks_provider() -> None:
    """Reset the cached JWKS key provider instance (useful for tests and reloads)."""
    global _jwks_provider, _jwks_provider_url
    _jwks_provider = None
    _jwks_provider_url = None


def get_jwks_provider() -> JwksKeyProvider:
    """Retrieve or initialize singleton JwksKeyProvider to retain cached keys."""
    global _jwks_provider, _jwks_provider_url
    url = settings.auth_jwks_url
    if _jwks_provider is None or _jwks_provider_url != url:
        _jwks_provider = JwksKeyProvider(
            jwks_url=url,
            cache_ttl_seconds=settings.auth_jwks_cache_ttl_seconds,
            refetch_cooldown_seconds=settings.auth_jwks_refetch_cooldown_seconds,
            timeout_seconds=settings.auth_jwks_timeout_seconds,
        )
        _jwks_provider_url = url
    return _jwks_provider


def get_key_provider() -> KeyProvider:
    """Build or retrieve KeyProvider based on auth_provider setting.

    Raises ValueError on configuration or file read errors to fail closed.
    """
    provider_type = (settings.auth_provider or "").lower().strip()

    if provider_type == "static":
        key_path = settings.auth_public_key_path
        if not key_path:
            raise ValueError("auth_public_key_path is not configured")
        try:
            with open(key_path, "r", encoding="utf-8") as f:
                public_pem = f.read()
            if not public_pem.strip():
                raise ValueError(f"Public key file is empty: {key_path}")
        except Exception as exc:
            raise ValueError(f"Failed to read public key from {key_path}: {exc}") from exc

        return StaticKeyProvider(public_key_pem=public_pem, kid=settings.auth_jwt_key_id)

    elif provider_type == "jwks":
        if not settings.auth_jwks_url:
            raise ValueError("auth_jwks_url is not configured")
        return get_jwks_provider()

    else:
        raise ValueError(f"Unsupported auth_provider: {provider_type}")


def get_token_verifier() -> TokenVerifier:
    """Build TokenVerifier from settings. Raises ValueError on misconfiguration."""
    provider = get_key_provider()
    return TokenVerifier(
        key_provider=provider,
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
        leeway_seconds=settings.auth_leeway_seconds,
    )


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
) -> Principal:
    """FastAPI dependency that returns the authenticated Principal.

    Verifies RS256 access JWT using libs/faultline-auth.
    Extracts active workspace_id and subject user_id from verified claims.
    """
    if credentials is None or not credentials.credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        verifier = get_token_verifier()
    except ValueError as exc:
        logger.error("Authentication configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    raw_token = credentials.credentials

    try:
        ctx: AuthContext = await verifier.verify(raw_token)
    except InvalidWorkspaceClaim as exc:
        logger.debug("Token rejected due to invalid workspace claim: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        ) from exc
    except KeysUnavailable as exc:
        logger.error("Authentication keys unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidToken as exc:
        logger.debug("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if ctx.workspace_id is None:
        logger.debug("Token missing workspace_id for user_id=%s", ctx.user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        )

    logger.debug("Authenticated user_id=%s workspace_id=%s", ctx.user_id, ctx.workspace_id)
    return Principal(user_id=ctx.user_id, workspace_id=ctx.workspace_id)
