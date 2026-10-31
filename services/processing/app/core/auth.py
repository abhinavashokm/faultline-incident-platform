from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

http_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    workspace_id: UUID


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
) -> Principal:
    """FastAPI dependency that returns the authenticated Principal.

    All routers depend ONLY on this dependency.
    If libs/faultline-auth is not installed or configured in this service,
    the default behavior FAILS CLOSED with 401 Unauthorized.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fail-closed default implementation:
    # libs/faultline-auth is not installed in services/processing,
    # so every un-overridden authenticated request is rejected with 401.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

