import asyncio
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.adapters.kafka import FakeKafkaProducer
from app.adapters.key_resolver import FakeProjectKeyResolver
from app.adapters.redis_limiter import FakeRateLimiter
from app.dependencies import (
    get_concurrency_semaphore,
    get_kafka_producer,
    get_key_resolver,
    get_rate_limiter,
)
from app.main import create_app


@pytest.fixture
def fake_kafka():
    producer = FakeKafkaProducer()
    producer._started = True
    return producer


@pytest.fixture
def fake_limiter():
    return FakeRateLimiter(limit=100, window_seconds=60)


@pytest.fixture
def fake_resolver():
    return FakeProjectKeyResolver()


@pytest.fixture
def test_workspace_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def test_project_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def test_public_key(fake_resolver, test_project_id, test_workspace_id) -> str:
    key = "fl_pub_test12345678"
    fake_resolver.add_key(key, project_id=test_project_id, workspace_id=test_workspace_id)
    return key


@pytest_asyncio.fixture
async def client(fake_kafka, fake_limiter, fake_resolver) -> AsyncIterator[AsyncClient]:
    app = create_app()
    semaphore = asyncio.Semaphore(100)

    app.dependency_overrides[get_kafka_producer] = lambda: fake_kafka
    app.dependency_overrides[get_rate_limiter] = lambda: fake_limiter
    app.dependency_overrides[get_key_resolver] = lambda: fake_resolver
    app.dependency_overrides[get_concurrency_semaphore] = lambda: semaphore

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
