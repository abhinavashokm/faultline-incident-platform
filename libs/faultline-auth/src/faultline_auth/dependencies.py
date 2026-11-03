import logging
from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from faultline_auth.context import AuthContext
from faultline_auth.errors import (
    AuthConfigurationError,
    InvalidToken,
    InvalidWorkspaceClaim,
    KeysUnavailable,
)
from faultline_auth.factory import get_token_verifier
from faultline_auth.jwt import TokenVerifier
from faultline_auth.principal import Principal

logger = logging.getLogger(__name__)

ROLE_RANK: dict[str, int] = {
    "owner": 4,
    "admin": 3,
    "member": 2,
    "viewer": 1,
}

http_bearer = HTTPBearer(auto_error=False)


async def _verify_credentials_with_verifier(
    credentials: HTTPAuthorizationCredentials | None,
    verifier: TokenVerifier,
) -> AuthContext:
    """Internal helper to verify Bearer credentials using a TokenVerifier.

    Enforces the shared error policy:
    - Missing, non-Bearer, or empty credentials -> 401 "Missing or invalid credentials"
    - InvalidWorkspaceClaim -> 403 "You do not have permission to access this resource"
    - InvalidToken -> 401 "Missing or invalid credentials"
    - KeysUnavailable -> 503 "Authentication temporarily unavailable"
    - AuthConfigurationError -> 500 "Internal server error"
    """
    if (
        credentials is None
        or not credentials.credentials
        or not credentials.credentials.strip()
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await verifier.verify(credentials.credentials)
    except InvalidWorkspaceClaim as exc:
        logger.debug("Token rejected due to invalid workspace claim: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        ) from exc
    except InvalidToken as exc:
        logger.debug("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except KeysUnavailable as exc:
        logger.error("Authentication keys unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication temporarily unavailable",
        ) from exc
    except AuthConfigurationError as exc:
        logger.error("Authentication configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
) -> Principal:
    """FastAPI dependency that returns the authenticated Principal.

    Verifies the RS256 Bearer JWT access token using the cached process-wide verifier.
    Extracts the subject user_id and active workspace_id.
    Fails closed with 403 if the workspace_id claim is missing from the token.
    """
    if (
        credentials is None
        or not credentials.credentials
        or not credentials.credentials.strip()
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        verifier = get_token_verifier()
    except AuthConfigurationError as exc:
        logger.error("Authentication configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc

    ctx = await _verify_credentials_with_verifier(credentials, verifier)

    try:
        return Principal.from_context(ctx)
    except ValueError as exc:
        logger.debug("Token missing workspace_id for user_id=%s: %s", ctx.user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        ) from exc


class AuthDependencies:
    """Builds FastAPI authentication and authorization dependencies using a TokenVerifier."""

    def __init__(self, verifier: TokenVerifier) -> None:
        self.verifier = verifier

    def current_user(self) -> Callable[..., Any]:
        """Dependency that verifies the Bearer token and returns the AuthContext."""

        async def _current_user(
            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
        ) -> AuthContext:
            return await _verify_credentials_with_verifier(credentials, self.verifier)

        return _current_user

    def require_workspace(self, param_name: str = "workspace_id") -> Callable[..., Any]:
        """Dependency that checks that the token's workspace_id matches the path parameter.
        Returns 404 on mismatch or missing workspace in token (never 403).
        """
        user_dep = self.current_user()

        async def _require_workspace(
            request: Request,
            ctx: Annotated[AuthContext, Depends(user_dep)],
        ) -> AuthContext:
            if ctx.workspace_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found",
                )

            path_param = request.path_params.get(param_name)
            if not path_param:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found",
                )

            try:
                expected_uuid = UUID(str(path_param))
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found",
                )

            if ctx.workspace_id != expected_uuid:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found",
                )

            return ctx

        return _require_workspace

    def require_role(self, min_role: str, param_name: str = "workspace_id") -> Callable[..., Any]:
        """Dependency that requires a minimum workspace role rank (owner > admin > member > viewer)."""
        workspace_dep = self.require_workspace(param_name=param_name)
        min_rank = ROLE_RANK.get(min_role, 0)

        async def _require_role(
            ctx: Annotated[AuthContext, Depends(workspace_dep)],
        ) -> AuthContext:
            user_rank = ROLE_RANK.get(ctx.role or "", 0)
            if user_rank < min_rank:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
            return ctx

        return _require_role
