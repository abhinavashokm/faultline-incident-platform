import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from app.core.config import Settings
from app.main import create_app
from app.middleware.rate_limit import MemoryRateLimiter, RedisRateLimiter
from tests.conftest import MockUpstreamState


@pytest.mark.asyncio
async def test_in_memory_rate_limit_exceeded_returns_429(
    base_settings: Settings,
    mock_upstream: MockUpstreamState,
):
    # Set limit to 3 requests in 60s
    settings = base_settings.model_copy(update={"rate_limit_requests": 3, "rate_limit_window_seconds": 60})
    app = create_app(custom_settings=settings)
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_upstream.handler))
    app.state.rate_limiter = MemoryRateLimiter(limit=3, window_seconds=60)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Request 1, 2, 3 should succeed
        for _ in range(3):
            resp = await client.get("/api/v1/projects")
            assert resp.status_code == 200

        # Request 4 exceeds rate limit
        resp_4 = await client.get("/api/v1/projects")
        assert resp_4.status_code == 429
        assert resp_4.json() == {"detail": "Too many requests"}
        assert "Retry-After" in resp_4.headers
        assert int(resp_4.headers["Retry-After"]) >= 1


@pytest.mark.asyncio
async def test_health_endpoint_is_exempt_from_rate_limiting(
    base_settings: Settings,
    mock_upstream: MockUpstreamState,
):
    # Set limit to 1 request
    settings = base_settings.model_copy(update={"rate_limit_requests": 1, "rate_limit_window_seconds": 60})
    app = create_app(custom_settings=settings)
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_upstream.handler))
    app.state.rate_limiter = MemoryRateLimiter(limit=1, window_seconds=60)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1st request consumes the limit for /api/v1/projects
        resp1 = await client.get("/api/v1/projects")
        assert resp1.status_code == 200

        # 2nd request to /api/v1/projects is blocked
        resp2 = await client.get("/api/v1/projects")
        assert resp2.status_code == 429

        # But /health continues to return 200 successfully
        for _ in range(5):
            resp_health = await client.get("/health")
            assert resp_health.status_code == 200
            assert resp_health.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_redis_failure_fails_open(
    base_settings: Settings,
    mock_upstream: MockUpstreamState,
):
    # Mock Redis client where script execution raises connection error
    mock_redis = MagicMock()
    mock_script = AsyncMock(side_effect=Exception("Redis connection refused"))
    mock_redis.register_script.return_value = mock_script

    redis_limiter = RedisRateLimiter(redis_client=mock_redis, limit=5, window_seconds=60)

    app = create_app(custom_settings=base_settings)
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_upstream.handler))
    app.state.rate_limiter = redis_limiter

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Request should succeed despite Redis failure (fail open)
        resp = await client.get("/api/v1/projects")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_client_ip_determination_trust_forwarded_for(
    base_settings: Settings,
    mock_upstream: MockUpstreamState,
):
    # With trust_forwarded_for=True, different XFF headers are separate IPs
    settings = base_settings.model_copy(
        update={"rate_limit_requests": 1, "rate_limit_window_seconds": 60, "trust_forwarded_for": True}
    )
    app = create_app(custom_settings=settings)
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_upstream.handler))
    app.state.rate_limiter = MemoryRateLimiter(limit=1, window_seconds=60)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # IP 1
        resp_ip1 = await client.get("/api/v1/projects", headers={"X-Forwarded-For": "203.0.113.195"})
        assert resp_ip1.status_code == 200

        # IP 1 again -> blocked
        resp_ip1_again = await client.get("/api/v1/projects", headers={"X-Forwarded-For": "203.0.113.195"})
        assert resp_ip1_again.status_code == 429

        # IP 2 -> succeeds because it is a different client IP
        resp_ip2 = await client.get("/api/v1/projects", headers={"X-Forwarded-For": "198.51.100.17"})
        assert resp_ip2.status_code == 200
