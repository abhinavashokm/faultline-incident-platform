import os
from collections.abc import AsyncIterator
from pathlib import Path

# Set default test secret before settings are loaded
os.environ.setdefault("CONTROL_PLANE_INTERNAL_SERVICE_SECRET", "test-internal-secret")

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Import all model modules so Base.metadata is complete before create_all runs
from app.auth import models as _auth_models  # noqa: F401
from app.projects import models as _projects_models  # noqa: F401
from app.workspaces import models as _workspaces_models  # noqa: F401

from app.api_main import app
from app.core.config import _read_key_file, settings
from app.core.db import Base, get_session
from app.core.integrations.email import EmailSender, get_email_sender

TEST_DATABASE_URL = os.getenv(
    "CONTROL_PLANE_TEST_DATABASE_URL",
    "postgresql+asyncpg://faultline:faultline@localhost:5432/control_plane_test",
)


@pytest.fixture(scope="session")
def test_keys(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str, Path, Path]:
    """Generate temporary RSA 2048 keypair for the test session."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    keys_dir = tmp_path_factory.mktemp("test_keys")
    priv_path = keys_dir / "private.pem"
    pub_path = keys_dir / "public.pem"
    priv_path.write_bytes(private_pem)
    pub_path.write_bytes(public_pem)

    settings.jwt_private_key_path = str(priv_path)
    settings.jwt_public_key_path = str(pub_path)
    _read_key_file.cache_clear()

    return private_pem.decode("utf-8"), public_pem.decode("utf-8"), priv_path, pub_path


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine(test_keys: tuple[str, str, Path, Path]) -> AsyncIterator[AsyncEngine]:
    """Initialize test database engine, create citext extension, control schema, and tables."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS control"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def truncate_tables(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """Truncate tables before and after each test to ensure test isolation."""
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE control.email_verification_codes, control.refresh_tokens, control.refresh_sessions, "
                "control.project_settings, control.project_api_keys, control.projects, "
                "control.workspace_members, control.workspaces, control.users CASCADE"
            )
        )
    yield
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE control.email_verification_codes, control.refresh_tokens, control.refresh_sessions, "
                "control.project_settings, control.project_api_keys, control.projects, "
                "control.workspace_members, control.workspaces, control.users CASCADE"
            )
        )


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent_emails: list[dict[str, object]] = []

    async def send_verification_code(
        self, to_email: str, code: str, expires_in_minutes: int = 10
    ) -> None:
        self.sent_emails.append(
            {
                "to_email": to_email,
                "code": code,
                "expires_in_minutes": expires_in_minutes,
            }
        )


@pytest.fixture
def fake_email_sender() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Provide a direct AsyncSession connected to the test database."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(
    test_engine: AsyncEngine,
    fake_email_sender: FakeEmailSender,
) -> AsyncIterator[AsyncClient]:
    """Provide an AsyncClient configured with test database session overrides."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_email_sender] = lambda: fake_email_sender
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

