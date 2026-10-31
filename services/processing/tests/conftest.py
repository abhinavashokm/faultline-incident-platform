import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

TEST_DB_URL = os.getenv(
    "PROCESSING_TEST_DATABASE_URL",
    settings.database_url,
)


@pytest.fixture
def test_workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def test_project_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine | None]:
    """Provide async database engine if database is reachable, otherwise None."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.database_schema}"))
        yield engine
    except Exception as exc:
        yield None
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(test_engine: AsyncEngine | None) -> async_sessionmaker[AsyncSession]:
    if test_engine is None:
        pytest.skip("Test database is not reachable at " + TEST_DB_URL)
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session

