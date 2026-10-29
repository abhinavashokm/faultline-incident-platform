import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshSession, RefreshToken, User
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    MembershipResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    WorkspaceSummary,
    WorkspaceWithRole,
)
from app.auth.security import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
    create_access_token,
    hash_password,
    hash_refresh_token,
    verify_dummy_password,
    verify_password,
)
from app.core.config import settings
from app.workspaces.repository import WorkspaceRepository
from app.workspaces.service import create_personal_workspace

logger = logging.getLogger(__name__)


class AuthService:
    """Service owning authentication business rules and database transactions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AuthRepository(session)

    async def signup(self, payload: SignupRequest) -> tuple[User, WorkspaceSummary]:
        async with self.session.begin():
            existing = await self.repository.get_by_email(payload.email)
            if existing is not None:
                logger.info("Signup conflict: email already registered")
                raise EmailAlreadyRegistered("Email already registered")

            user = User(
                id=uuid.uuid4(),
                email=payload.email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name,
                status="active",
            )
            try:
                await self.repository.create(user)
            except IntegrityError as exc:
                logger.info("Signup race condition: unique constraint violation on email")
                raise EmailAlreadyRegistered("Email already registered") from exc

            workspace, _ = await create_personal_workspace(self.session, user)
            logger.info(
                "User registered successfully: user_id=%s, workspace_id=%s",
                user.id,
                workspace.id,
            )
            summary = WorkspaceSummary(
                id=workspace.id,
                name=workspace.name,
                slug=workspace.slug,
            )
            return user, summary

    async def login(self, payload: LoginRequest) -> TokenResponse:
        async with self.session.begin():
            user = await self.repository.get_by_email(payload.email)
            if user is None:
                verify_dummy_password(payload.password)
                logger.info("Login failed: unknown email")
                raise InvalidCredentials("Invalid email or password")

            if not verify_password(payload.password, user.password_hash or ""):
                logger.info("Login failed: invalid password for user_id=%s", user.id)
                raise InvalidCredentials("Invalid email or password")

            if user.status != "active":
                logger.info(
                    "Login failed: inactive user status=%s for user_id=%s",
                    user.status,
                    user.id,
                )
                raise InvalidCredentials("Invalid email or password")

            now = datetime.now(timezone.utc)
            await self.repository.update_last_login(user.id, now)

            # Create RefreshSession
            session_expires_at = now + timedelta(days=settings.refresh_token_ttl_days)
            refresh_session = RefreshSession(
                id=uuid.uuid4(),
                user_id=user.id,
                created_at=now,
                expires_at=session_expires_at,
            )
            await self.repository.create_refresh_session(refresh_session)

            # Create first RefreshToken (opaque 48 urlsafe bytes, store sha256 hex)
            raw_refresh_token = secrets.token_urlsafe(48)
            token_hash = hash_refresh_token(raw_refresh_token)
            token_record = RefreshToken(
                id=uuid.uuid4(),
                session_id=refresh_session.id,
                token_hash=token_hash,
                created_at=now,
                expires_at=session_expires_at,
            )
            await self.repository.create_refresh_token(token_record)

            # Resolve membership
            ws_repo = WorkspaceRepository(self.session)
            memberships = await ws_repo.get_memberships(user.id)
            workspace_info = None
            workspace_id = None
            role = None
            if memberships:
                first_member, first_workspace = memberships[0]
                workspace_id = first_workspace.id
                role = first_member.role
                workspace_info = WorkspaceWithRole(
                    id=first_workspace.id,
                    name=first_workspace.name,
                    slug=first_workspace.slug,
                    role=first_member.role,
                )

            # Issue access token
            ttl = timedelta(minutes=settings.access_token_ttl_minutes)
            access_token = create_access_token(
                user_id=user.id,
                workspace_id=workspace_id,
                role=role,
                sid=refresh_session.id,
                ttl=ttl,
                now=now,
            )
            logger.info("User logged in successfully: user_id=%s", user.id)
            return TokenResponse(
                access_token=access_token,
                refresh_token=raw_refresh_token,
                token_type="bearer",
                expires_in=int(ttl.total_seconds()),
                workspace=workspace_info,
            )

    async def refresh(self, payload: RefreshRequest) -> TokenResponse:
        token_hash = hash_refresh_token(payload.refresh_token)

        if not self.session.in_transaction():
            await self.session.begin()

        token_data = await self.repository.get_refresh_token_by_hash(token_hash)
        if token_data is None:
            logger.info("Refresh failed: token hash not found")
            await self.session.rollback()
            raise InvalidRefreshToken("Invalid refresh token")

        refresh_token_row, refresh_session = token_data

        # Atomically claim the token
        claimed = await self.repository.claim_refresh_token(refresh_token_row.id)
        if not claimed:
            # REUSE detected: revoke session and commit before returning
            logger.warning(
                "Refresh token reuse detected for session_id=%s, token_id=%s. Revoking session.",
                refresh_session.id,
                refresh_token_row.id,
            )
            await self.repository.revoke_session(refresh_session.id, "reuse_detected")
            await self.session.commit()
            raise InvalidRefreshToken("Invalid refresh token")

        now = datetime.now(timezone.utc)

        # Check session revoked or expired, or token expired
        if refresh_session.revoked_at is not None:
            logger.info("Refresh failed: session %s already revoked", refresh_session.id)
            await self.session.rollback()
            raise InvalidRefreshToken("Invalid refresh token")

        if refresh_session.expires_at <= now:
            logger.info("Refresh failed: session %s expired", refresh_session.id)
            await self.session.rollback()
            raise InvalidRefreshToken("Invalid refresh token")

        if refresh_token_row.expires_at <= now:
            logger.info("Refresh failed: token %s expired", refresh_token_row.id)
            await self.session.rollback()
            raise InvalidRefreshToken("Invalid refresh token")

        # Reload user
        user = await self.repository.get_by_id(refresh_session.user_id)
        if user is None or user.status != "active":
            logger.warning(
                "Refresh failed: user %s inactive or missing. Revoking session.",
                refresh_session.user_id,
            )
            await self.repository.revoke_session(refresh_session.id, "user_disabled")
            await self.session.commit()
            raise InvalidRefreshToken("Invalid refresh token")

        # Re-resolve memberships
        ws_repo = WorkspaceRepository(self.session)
        memberships = await ws_repo.get_memberships(user.id)
        workspace_info = None
        workspace_id = None
        role = None
        if memberships:
            first_member, first_workspace = memberships[0]
            workspace_id = first_workspace.id
            role = first_member.role
            workspace_info = WorkspaceWithRole(
                id=first_workspace.id,
                name=first_workspace.name,
                slug=first_workspace.slug,
                role=first_member.role,
            )

        # Issue a new RefreshToken in the SAME session
        raw_new_refresh_token = secrets.token_urlsafe(48)
        new_token_hash = hash_refresh_token(raw_new_refresh_token)
        new_token_record = RefreshToken(
            id=uuid.uuid4(),
            session_id=refresh_session.id,
            token_hash=new_token_hash,
            created_at=now,
            expires_at=refresh_session.expires_at,
        )
        await self.repository.create_refresh_token(new_token_record)
        await self.repository.update_session_last_used(refresh_session.id)

        # Commit rotation transaction
        await self.session.commit()

        # Issue new access token
        ttl = timedelta(minutes=settings.access_token_ttl_minutes)
        access_token = create_access_token(
            user_id=user.id,
            workspace_id=workspace_id,
            role=role,
            sid=refresh_session.id,
            ttl=ttl,
            now=now,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_new_refresh_token,
            token_type="bearer",
            expires_in=int(ttl.total_seconds()),
            workspace=workspace_info,
        )

    async def logout(self, payload: LogoutRequest) -> None:
        token_hash = hash_refresh_token(payload.refresh_token)
        async with self.session.begin():
            token_data = await self.repository.get_refresh_token_by_hash(token_hash)
            if token_data is not None:
                _, refresh_session = token_data
                if refresh_session.revoked_at is None:
                    await self.repository.revoke_session(refresh_session.id, "logout")
                    logger.info("Session %s revoked on logout", refresh_session.id)

    async def get_me(
        self,
        user_id: uuid.UUID,
        token_workspace_id: uuid.UUID | None,
        token_role: str | None,
    ) -> CurrentUserResponse:
        user = await self.repository.get_by_id(user_id)
        if user is None or user.status != "active":
            raise InvalidCredentials("User not found or inactive")

        ws_repo = WorkspaceRepository(self.session)
        memberships = await ws_repo.get_memberships(user.id)
        membership_list = [
            MembershipResponse(
                workspace_id=w.id,
                name=w.name,
                slug=w.slug,
                role=m.role,
            )
            for m, w in memberships
        ]

        workspace_info = None
        if token_workspace_id is not None:
            matching = next(
                ((m, w) for m, w in memberships if w.id == token_workspace_id), None
            )
            if matching is not None:
                m, w = matching
                workspace_info = WorkspaceWithRole(
                    id=w.id,
                    name=w.name,
                    slug=w.slug,
                    role=token_role or m.role,
                )

        return CurrentUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            email_verified_at=user.email_verified_at,
            created_at=user.created_at,
            workspace=workspace_info,
            memberships=membership_list,
        )
