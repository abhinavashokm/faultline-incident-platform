from unittest.mock import AsyncMock
import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.kafka import FakeKafkaProducer
from app.dependencies import get_kafka_producer, get_redis_client
from app.main import create_app


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_healthy():
    app = create_app()
    fake_kafka = FakeKafkaProducer()
    fake_kafka._started = True

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    app.dependency_overrides[get_kafka_producer] = lambda: fake_kafka
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/readyz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "kafka": "ok", "redis": "ok"}


@pytest.mark.asyncio
async def test_readyz_kafka_unhealthy():
    app = create_app()
    fake_kafka = FakeKafkaProducer()
    fake_kafka._started = False  # Not started

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    app.dependency_overrides[get_kafka_producer] = lambda: fake_kafka
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/readyz")
        assert response.status_code == 503
        assert "Kafka producer not running" in response.json()["detail"]


@pytest.mark.asyncio
async def test_readyz_redis_unhealthy():
    app = create_app()
    fake_kafka = FakeKafkaProducer()
    fake_kafka._started = True

    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = ConnectionError("Redis unreachable")

    app.dependency_overrides[get_kafka_producer] = lambda: fake_kafka
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/readyz")
        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]

