import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import (
    EmailVerificationCode,
    RefreshSession,
    RefreshToken,
    User,
)
from app.auth.repository import AuthRepository, EmailVerificationRepository
from app.auth.schemas import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    MembershipResponse,
    RefreshRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SignupRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    WorkspaceSummary,
    WorkspaceWithRole,
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
    create_access_token,
    hash_password,
    hash_refresh_token,
    verify_dummy_password,
    verify_password,
)
from app.core.config import settings
from app.core.integrations.email import EmailSender, get_email_sender
from app.core.security import generate_otp, hash_otp, verify_otp
from app.core.uuid7 import uuid7
from app.workspaces.repository import WorkspaceRepository
from app.workspaces.service import create_personal_workspace

logger = logging.getLogger(__name__)


class AuthService:
    """Service owning authentication business rules and database transactions."""

    def __init__(
        self,
        session: AsyncSession,
        email_sender: EmailSender | None = None,
    ) -> None:
        self.session = session
        self.repository = AuthRepository(session)
        self.verification_repo = EmailVerificationRepository(session)
        self.email_sender = email_sender or get_email_sender()

    async def _send_verification_email_safe(self, to_email: str, code: str) -> None:
        """Helper to send verification email without failing the caller if sending fails."""
        try:
            await self.email_sender.send_verification_code(
                to_email,
                code,
                expires_in_minutes=settings.otp_ttl_seconds // 60,
            )
        except Exception as exc:
            # Never log the raw code
            logger.error("Failed to send verification email to %s: %s", to_email, exc)

    async def signup(
        self,
        payload: SignupRequest,
        background_tasks: BackgroundTasks | None = None,
    ) -> tuple[User, WorkspaceSummary]:
        raw_code = generate_otp()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=settings.otp_ttl_seconds)

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
                email_verified_at=None,
            )
            try:
                await self.repository.create(user)
            except IntegrityError as exc:
                logger.info("Signup race condition: unique constraint violation on email")
                raise EmailAlreadyRegistered("Email already registered") from exc

            workspace, _ = await create_personal_workspace(self.session, user)

            code_hash = hash_otp(user.id, raw_code)
            verification_code = EmailVerificationCode(
                id=uuid7(),
                user_id=user.id,
                code_hash=code_hash,
                attempts=0,
                created_at=now,
                expires_at=expires_at,
            )
            await self.verification_repo.create(verification_code)

        logger.info(
            "User registered successfully: user_id=%s, workspace_id=%s",
            user.id,
            workspace.id,
        )

        # Send the email only AFTER the commit via BackgroundTasks
        if background_tasks is not None:
            background_tasks.add_task(
                self._send_verification_email_safe, user.email, raw_code
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

            if user.email_verified_at is None:
                logger.info("Login failed: email not verified for user_id=%s", user.id)
                raise EmailNotVerified("email_not_verified")

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

    async def verify_email(
        self, payload: VerifyEmailRequest
    ) -> VerifyEmailResponse:
        now = datetime.now(timezone.utc)
        error_to_raise: Exception | None = None
        response: VerifyEmailResponse | None = None

        async with self.session.begin():
            user = await self.repository.get_by_email(payload.email)
            if user is None or user.status != "active":
                logger.info("Verify email: unknown or inactive user")
                raise InvalidVerificationCode("Invalid or expired verification code")

            if user.email_verified_at is not None:
                logger.info("Verify email: user %s already verified", user.id)
                return VerifyEmailResponse(
                    message="Email verified",
                    email_verified_at=user.email_verified_at.isoformat(),
                )

            code_record = await self.verification_repo.get_active_by_user_id(
                user.id, for_update=True
            )
            if code_record is None:
                logger.info("Verify email: no active code for user %s", user.id)
                raise InvalidVerificationCode("Invalid or expired verification code")

            code_expires_at = code_record.expires_at
            if code_expires_at.tzinfo is None:
                code_expires_at = code_expires_at.replace(tzinfo=timezone.utc)

            if code_expires_at <= now:
                logger.info("Verify email: code expired for user %s", user.id)
                raise InvalidVerificationCode("Invalid or expired verification code")

            if code_record.attempts >= settings.otp_max_attempts:
                logger.warning(
                    "Verify email: code already reached max attempts for user %s",
                    user.id,
                )
                await self.verification_repo.mark_consumed(
                    code_record.id, consumed_at=now
                )
                error_to_raise = TooManyVerificationAttempts(
                    "Too many attempts. Request a new code."
                )
            elif not verify_otp(user.id, payload.code, code_record.code_hash):
                new_attempts = await self.verification_repo.increment_attempts(
                    code_record.id
                )
                if new_attempts >= settings.otp_max_attempts:
                    await self.verification_repo.mark_consumed(
                        code_record.id, consumed_at=now
                    )
                    error_to_raise = TooManyVerificationAttempts(
                        "Too many attempts. Request a new code."
                    )
                else:
                    error_to_raise = InvalidVerificationCode(
                        "Invalid or expired verification code"
                    )
            else:
                await self.verification_repo.mark_consumed(
                    code_record.id, consumed_at=now
                )
                await self.repository.update_email_verified_at(user.id, now)
                response = VerifyEmailResponse(
                    message="Email verified",
                    email_verified_at=now.isoformat(),
                )

        if error_to_raise is not None:
            raise error_to_raise

        return response  # type: ignore[return-value]

    async def resend_verification(
        self,
        payload: ResendVerificationRequest,
        background_tasks: BackgroundTasks | None = None,
    ) -> ResendVerificationResponse:
        now = datetime.now(timezone.utc)
        raw_code: str | None = None

        async with self.session.begin():
            user = await self.repository.get_by_email(payload.email)
            # Unknown, suspended/deleted, or already verified account: return 202 and send nothing
            if user is None or user.status != "active" or user.email_verified_at is not None:
                logger.info(
                    "Resend verification ignored for %s (unknown, inactive, or already verified)",
                    payload.email,
                )
                return ResendVerificationResponse()

            # Check cooldown on latest code
            latest_code = await self.verification_repo.get_latest_code_by_user_id(user.id)
            if latest_code is not None:
                created_at = latest_code.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                elapsed = (now - created_at).total_seconds()
                if elapsed < settings.otp_resend_cooldown_seconds:
                    retry_after = max(1, int(settings.otp_resend_cooldown_seconds - elapsed))
                    logger.info(
                        "Resend cooldown active for user %s: retry in %ss",
                        user.id,
                        retry_after,
                    )
                    raise VerificationCooldown(
                        "Please wait before requesting another code.",
                        retry_after=retry_after,
                    )

            # Check hourly cap
            one_hour_ago = now - timedelta(hours=1)
            recent_count = await self.verification_repo.count_codes_since(
                user.id, one_hour_ago
            )
            if recent_count >= settings.otp_resend_hourly_cap:
                logger.info(
                    "Resend hourly cap reached for user %s (%s codes in last hour)",
                    user.id,
                    recent_count,
                )
                raise VerificationHourlyCapExceeded(
                    "Please wait before requesting another code.",
                    retry_after=settings.otp_resend_cooldown_seconds,
                )

            active_code = await self.verification_repo.get_active_by_user_id(
                user.id, for_update=True
            )
            if active_code is not None:
                await self.verification_repo.mark_consumed(
                    active_code.id, consumed_at=now
                )

            raw_code = generate_otp()
            code_hash = hash_otp(user.id, raw_code)
            expires_at = now + timedelta(seconds=settings.otp_ttl_seconds)

            new_code = EmailVerificationCode(
                id=uuid7(),
                user_id=user.id,
                code_hash=code_hash,
                attempts=0,
                created_at=now,
                expires_at=expires_at,
            )
            await self.verification_repo.create(new_code)

        # Transaction committed! Send email after commit via BackgroundTasks
        if raw_code is not None and background_tasks is not None:
            background_tasks.add_task(
                self._send_verification_email_safe, payload.email, raw_code
            )

        return ResendVerificationResponse()


