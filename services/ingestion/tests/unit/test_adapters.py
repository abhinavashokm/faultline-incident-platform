import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.adapters.key_resolver import (
    CachedHttpProjectKeyResolver,
    InvalidKeyError,
    KeyResolverUnavailableError,
)
from app.adapters.redis_limiter import RedisRateLimiter


@pytest.mark.asyncio
async def test_cached_resolver_cache_hit():
    mock_redis = AsyncMock()
    mock_http = AsyncMock()

    proj_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    mock_redis.get.return_value = json.dumps({
        "status": "valid",
        "project_id": str(proj_id),
        "workspace_id": str(ws_id),
    })

    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
    )

    resolved = await resolver.resolve("test_public_key")
    assert resolved.project_id == proj_id
    assert resolved.workspace_id == ws_id
    mock_http.get.assert_not_called()


@pytest.mark.asyncio
async def test_cached_resolver_cache_miss_http_success():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss

    proj_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    mock_resp = httpx.Response(
        status_code=200,
        json={"project_id": str(proj_id), "workspace_id": str(ws_id), "revoked": False},
        request=httpx.Request("GET", "http://test"),
    )
    mock_http = AsyncMock()
    mock_http.get.return_value = mock_resp

    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
        service_token="test-token",
        cache_ttl=300,
    )

    resolved = await resolver.resolve("test_public_key")
    assert resolved.project_id == proj_id
    assert resolved.workspace_id == ws_id

    # Verify HTTP request was made with service token
    mock_http.get.assert_called_once()
    args, kwargs = mock_http.get.call_args
    assert kwargs["headers"]["X-Service-Token"] == "test-token"

    # Verify Redis cache write
    mock_redis.set.assert_called_once()
    set_args, set_kwargs = mock_redis.set.call_args
    assert set_kwargs["ex"] == 300


@pytest.mark.asyncio
async def test_cached_resolver_http_404_negative_cache():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    mock_resp = httpx.Response(
        status_code=404,
        json={"detail": "Key not found"},
        request=httpx.Request("GET", "http://test"),
    )
    mock_http = AsyncMock()
    mock_http.get.return_value = mock_resp

    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
        negative_cache_ttl=60,
    )

    with pytest.raises(InvalidKeyError):
        await resolver.resolve("unknown_key")

    # Verify negative cache was written
    mock_redis.set.assert_called_once()
    set_args, set_kwargs = mock_redis.set.call_args
    assert json.loads(set_args[1])["status"] == "not_found"
    assert set_kwargs["ex"] == 60


@pytest.mark.asyncio
async def test_cached_resolver_redis_error_falls_through_to_http():
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = RedisConnectionError("Redis connection lost")

    proj_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    mock_resp = httpx.Response(
        status_code=200,
        json={"project_id": str(proj_id), "workspace_id": str(ws_id), "revoked": False},
        request=httpx.Request("GET", "http://test"),
    )
    mock_http = AsyncMock()
    mock_http.get.return_value = mock_resp

    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
    )

    # Should not raise Redis error; falls through to HTTP successfully
    resolved = await resolver.resolve("test_key")
    assert resolved.project_id == proj_id
    mock_http.get.assert_called_once()


@pytest.mark.asyncio
async def test_redis_limiter_lua_execution():
    mock_redis = AsyncMock()
    mock_script = AsyncMock()
    mock_script.return_value = [1, 60]  # [allowed, ttl]
    mock_redis.register_script = MagicMock(return_value=mock_script)

    limiter = RedisRateLimiter(redis_client=mock_redis, limit=100, window_seconds=60)
    allowed, retry_after = await limiter.is_allowed(uuid.uuid4())
    assert allowed is True
    assert retry_after == 0


@pytest.mark.asyncio
async def test_redis_limiter_redis_error_fails_open():
    mock_redis = AsyncMock()
    mock_script = AsyncMock()
    mock_script.side_effect = RedisConnectionError("Redis down")
    mock_redis.register_script = MagicMock(return_value=mock_script)

    limiter = RedisRateLimiter(redis_client=mock_redis, limit=100, window_seconds=60)
    allowed, retry_after = await limiter.is_allowed(uuid.uuid4())
    # Fails open!
    assert allowed is True
    assert retry_after == 0
