from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from faultline_auth.context import AuthContext
from faultline_auth.errors import InvalidToken, KeysUnavailable
from faultline_auth.jwt import TokenVerifier

ROLE_RANK: dict[str, int] = {
    "owner": 4,
    "admin": 3,
    "member": 2,
    "viewer": 1,
}

http_bearer = HTTPBearer(auto_error=False)


class AuthDependencies:
    """Builds FastAPI authentication and authorization dependencies using a TokenVerifier."""

    def __init__(self, verifier: TokenVerifier) -> None:
        self.verifier = verifier

    def current_user(self) -> Callable[..., Any]:
        """Dependency that verifies the Bearer token and returns the AuthContext."""

        async def _current_user(
            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
        ) -> AuthContext:
            if credentials is None or not credentials.credentials:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                return await self.verifier.verify(credentials.credentials)
            except InvalidToken as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(exc),
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            except KeysUnavailable as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication temporarily unavailable",
                ) from exc

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

