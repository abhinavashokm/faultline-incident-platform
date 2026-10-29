import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshSession, RefreshToken, User


class AuthRepository:
    """Repository for user authentication, profile data, and refresh sessions.
    Contains queries only and never commits transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_last_login(self, user_id: uuid.UUID, last_login_at: datetime) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=last_login_at, updated_at=func.now())
        )
        await self.session.execute(stmt)

    async def create_refresh_session(
        self, refresh_session: RefreshSession
    ) -> RefreshSession:
        self.session.add(refresh_session)
        await self.session.flush()
        return refresh_session

    async def get_session_by_id(
        self, session_id: uuid.UUID
    ) -> RefreshSession | None:
        stmt = select(RefreshSession).where(RefreshSession.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_token_by_hash(
        self, token_hash: str
    ) -> tuple[RefreshToken, RefreshSession] | None:
        query = (
            select(RefreshToken, RefreshSession)
            .join(RefreshSession, RefreshToken.session_id == RefreshSession.id)
            .where(RefreshToken.token_hash == token_hash)
        )
        result = await self.session.execute(query)
        row = result.first()
        return (row[0], row[1]) if row is not None else None

    async def claim_refresh_token(self, token_id: uuid.UUID) -> bool:
        """Atomically mark token as used if it was not already used.
        Returns True if claimed, False if already used or missing.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id, RefreshToken.used_at.is_(None))
            .values(used_at=func.now())
            .returning(RefreshToken.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def revoke_session(self, session_id: uuid.UUID, reason: str) -> None:
        stmt = (
            update(RefreshSession)
            .where(RefreshSession.id == session_id)
            .values(revoked_at=func.now(), revoked_reason=reason)
        )
        await self.session.execute(stmt)

    async def update_session_last_used(self, session_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshSession)
            .where(RefreshSession.id == session_id)
            .values(last_used_at=func.now())
        )
        await self.session.execute(stmt)
