from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, current_user
from app.auth.schemas import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.security import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
)
from app.auth.service import AuthService
from app.core.db import get_session

router = APIRouter()


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
)
async def signup(
    payload: SignupRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    service = AuthService(session)
    try:
        user, workspace = await service.signup(payload)
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            created_at=user.created_at,
            workspace=workspace,
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    service = AuthService(session)
    try:
        return await service.login(payload)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
)
async def refresh(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    service = AuthService(session)
    try:
        return await service.refresh(payload)
    except InvalidRefreshToken as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    payload: LogoutRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    service = AuthService(session)
    await service.logout(payload)


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=CurrentUserResponse,
)
async def get_me(
    ctx: Annotated[AuthContext, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentUserResponse:
    service = AuthService(session)
    try:
        return await service.get_me(
            user_id=ctx.user_id,
            token_workspace_id=ctx.workspace_id,
            token_role=ctx.role,
        )
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
