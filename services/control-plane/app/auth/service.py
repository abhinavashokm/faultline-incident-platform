import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repository import AuthRepository
from app.auth.schemas import LoginRequest, SignupRequest, TokenResponse
from app.auth.security import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidToken,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Service owning authentication business rules and database transactions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AuthRepository(session)

    async def signup(self, payload: SignupRequest) -> User:
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

            logger.info("User registered successfully: user_id=%s", user.id)
            return user

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

            ttl = timedelta(minutes=settings.access_token_ttl_minutes)
            token = create_access_token(
                user_id=user.id,
                workspaces=[],
                ttl=ttl,
                now=now,
            )
            logger.info("User logged in successfully: user_id=%s", user.id)
            return TokenResponse(
                access_token=token,
                token_type="bearer",
                expires_in=int(ttl.total_seconds()),
            )

    async def get_user_from_token(self, token: str) -> User:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            raise InvalidToken("Invalid token: missing subject claim")

        try:
            user_id = uuid.UUID(sub)
        except (ValueError, TypeError) as exc:
            raise InvalidToken("Invalid token: subject is not a valid UUID") from exc

        user = await self.repository.get_by_id(user_id)
        if user is None:
            logger.info("User verification failed: user_id=%s not found", user_id)
            raise InvalidToken("User no longer exists or is not active")

        if user.status != "active":
            logger.info(
                "User verification failed: user_id=%s status=%s is not active",
                user_id,
                user.status,
            )
            raise InvalidToken("User no longer exists or is not active")

        return user

