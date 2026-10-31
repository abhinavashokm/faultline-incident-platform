from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, current_user
from app.auth.schemas import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.auth.security import (
    EmailAlreadyRegistered,
    EmailNotVerified,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidVerificationCode,
    TooManyVerificationAttempts,
    VerificationCooldown,
    VerificationHourlyCapExceeded,
)
from app.auth.service import AuthService
from app.core.db import get_session
from app.core.integrations.email import EmailSender, get_email_sender

router = APIRouter()


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
)
async def signup(
    payload: SignupRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    background_tasks: BackgroundTasks,
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> UserResponse:
    service = AuthService(session, email_sender=email_sender)
    try:
        user, workspace = await service.signup(
            payload, background_tasks=background_tasks
        )
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
    "/verify-email",
    status_code=status.HTTP_200_OK,
    response_model=VerifyEmailResponse,
)
async def verify_email(
    payload: VerifyEmailRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VerifyEmailResponse:
    service = AuthService(session)
    try:
        return await service.verify_email(payload)
    except InvalidVerificationCode as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        ) from exc
    except TooManyVerificationAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new code.",
        ) from exc


@router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ResendVerificationResponse,
)
async def resend_verification(
    payload: ResendVerificationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    background_tasks: BackgroundTasks,
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> ResendVerificationResponse:
    service = AuthService(session, email_sender=email_sender)
    try:
        return await service.resend_verification(
            payload, background_tasks=background_tasks
        )
    except (VerificationCooldown, VerificationHourlyCapExceeded) as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another code.",
            headers=headers,
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
    except EmailNotVerified as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="email_not_verified",
        ) from exc
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
