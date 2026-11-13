import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from faultline_auth import Principal, get_principal
from app.core.config import settings
from app.core.db import get_session
from app.delivery.email import EmailSender, get_email_sender
from app.main import create_app

TEST_DB_URL = os.getenv(
    "ALERTING_TEST_DATABASE_URL",
    settings.database_url,
)


@pytest.fixture
def test_workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def test_project_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def test_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth_principal(test_workspace_id: uuid.UUID, test_user_id: uuid.UUID) -> Principal:
    return Principal(user_id=test_user_id, workspace_id=test_workspace_id)


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine | None]:
    """Provide async database engine if test database is reachable, otherwise None."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.database_schema}"))
        yield engine
    except Exception:
        yield None
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(test_engine: AsyncEngine | None) -> async_sessionmaker[AsyncSession]:
    if test_engine is None:
        pytest.skip(f"Test database is not reachable at {TEST_DB_URL}")
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


class FakeEmailSender:
    def __init__(self, should_fail: bool = False) -> None:
        self.sent_emails: list[dict[str, str]] = []
        self.should_fail = should_fail

    async def send(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None:
        if self.should_fail:
            raise ConnectionError("SMTP server down")
        self.sent_emails.append(
            {
                "to_email": to_email,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body,
            }
        )


@pytest.fixture
def fake_email_sender() -> FakeEmailSender:
    return FakeEmailSender()


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    auth_principal: Principal,
    fake_email_sender: FakeEmailSender,
) -> AsyncIterator[AsyncClient]:
    """Client with authenticated principal dependency pre-configured."""
    app = create_app()

    async def _test_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _test_get_session
    app.dependency_overrides[get_principal] = lambda: auth_principal
    app.dependency_overrides[get_email_sender] = lambda: fake_email_sender

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def unauth_client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    """Client without authentication override to test unauthenticated rejection."""
    app = create_app()

    async def _test_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _test_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
