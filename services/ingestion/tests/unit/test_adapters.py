import asyncio
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

    resolved = await resolver.resolve("test_project_api_key")
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

    resolved = await resolver.resolve("test_project_api_key")
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


@pytest.mark.asyncio
async def test_cached_resolver_sends_service_token_header():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_http = AsyncMock()
    proj_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    mock_http.get.return_value = httpx.Response(
        status_code=200,
        json={"project_id": str(proj_id), "workspace_id": str(ws_id), "revoked": False},
        request=httpx.Request("GET", "http://test"),
    )
    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
        service_token="super-secret-token",
    )
    await resolver.resolve("test_key_123")
    mock_http.get.assert_called_once()
    _, kwargs = mock_http.get.call_args
    assert kwargs["headers"]["X-Service-Token"] == "super-secret-token"


@pytest.mark.asyncio
async def test_cached_resolver_http_401_misconfiguration_no_cache():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_http = AsyncMock()
    mock_http.get.return_value = httpx.Response(
        status_code=401,
        json={"detail": "Missing or invalid service token"},
        request=httpx.Request("GET", "http://test"),
    )
    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
        service_token="wrong-token",
    )
    with pytest.raises(KeyResolverUnavailableError) as exc_info:
        await resolver.resolve("test_key_401")
    assert "authentication misconfigured" in str(exc_info.value)
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_cached_resolver_http_403_misconfiguration_no_cache():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_http = AsyncMock()
    mock_http.get.return_value = httpx.Response(
        status_code=403,
        json={"detail": "Forbidden"},
        request=httpx.Request("GET", "http://test"),
    )
    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
        service_token="forbidden-token",
    )
    with pytest.raises(KeyResolverUnavailableError) as exc_info:
        await resolver.resolve("test_key_403")
    assert "authentication misconfigured" in str(exc_info.value)
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_cached_resolver_http_500_server_error_no_cache():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_http = AsyncMock()
    mock_http.get.return_value = httpx.Response(
        status_code=500,
        text="Internal Server Error",
        request=httpx.Request("GET", "http://test"),
    )
    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
    )
    with pytest.raises(KeyResolverUnavailableError):
        await resolver.resolve("test_key_500")
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_cached_resolver_connection_error_no_cache():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_http = AsyncMock()
    mock_http.get.side_effect = httpx.ConnectError("Failed to connect to Control Plane")

    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
    )
    with pytest.raises(KeyResolverUnavailableError):
        await resolver.resolve("test_key_conn_err")
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_cached_resolver_does_not_log_secret_or_full_key(caplog):
    import logging
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_http = AsyncMock()
    mock_http.get.return_value = httpx.Response(
        status_code=401,
        json={"detail": "Unauthorized"},
        request=httpx.Request("GET", "http://test"),
    )
    secret_value = "super-confidential-secret-9999"
    full_key = "fl_pub_1234567890abcdef12345678"
    resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
        service_token=secret_value,
    )
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(KeyResolverUnavailableError):
            await resolver.resolve(full_key)

    # Check that neither secret nor full project API key appears in any captured log message
    for record in caplog.records:
        assert secret_value not in record.message
        assert full_key not in record.message


def test_ingestion_settings_fails_without_service_token(monkeypatch):
    from pydantic import ValidationError
    from app.core.config import Settings
    monkeypatch.delenv("CONTROL_PLANE_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("CONTROL_PLANE_INTERNAL_SERVICE_SECRET", raising=False)
    monkeypatch.delenv("INTERNAL_SERVICE_SECRET", raising=False)
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.asyncio
async def test_aiokafka_producer_adapter_lazy_start_on_publish():
    from app.adapters.kafka import AIOKafkaProducerAdapter, ProducerState

    adapter = AIOKafkaProducerAdapter(
        bootstrap_servers="mock:9092",
        timeout_seconds=1.0,
        connect_timeout_seconds=1.0,
        reconnect_cooldown_seconds=1.0,
    )
    assert adapter._state == ProducerState.STOPPED

    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock()
    mock_producer.send_and_wait = AsyncMock()

    with patch("app.adapters.kafka.AIOKafkaProducer", return_value=mock_producer):
        await adapter.publish("test-topic", b"key", b"value")

    assert adapter._state == ProducerState.RUNNING
    mock_producer.start.assert_called_once()
    mock_producer.send_and_wait.assert_called_once_with("test-topic", value=b"value", key=b"key")
    assert await adapter.is_healthy() is True

    await adapter.stop()
    assert adapter._state == ProducerState.STOPPED
    mock_producer.stop.assert_called_once()


@pytest.mark.asyncio
async def test_aiokafka_producer_adapter_failed_start_cooldown_and_recovery():
    import time
    from app.adapters.kafka import AIOKafkaProducerAdapter, KafkaPublishError, ProducerState

    adapter = AIOKafkaProducerAdapter(
        bootstrap_servers="mock:9092",
        timeout_seconds=0.5,
        connect_timeout_seconds=0.5,
        reconnect_cooldown_seconds=0.2,
    )

    mock_failing_producer = AsyncMock()
    mock_failing_producer.start = AsyncMock(side_effect=ConnectionError("Cannot reach Kafka"))
    mock_failing_producer.stop = AsyncMock()

    with patch("app.adapters.kafka.AIOKafkaProducer", return_value=mock_failing_producer):
        with pytest.raises(KafkaPublishError) as exc_info:
            await adapter.publish("test-topic", b"key", b"val")
        assert "Kafka producer failed to start" in str(exc_info.value)
        assert adapter._state == ProducerState.FAILED
        assert await adapter.is_healthy() is False

        # Attempting again immediately hits cooldown without calling AIOKafkaProducer
        with pytest.raises(KafkaPublishError) as exc_info_cooldown:
            await adapter.publish("test-topic", b"key", b"val")
        assert "cooldown active" in str(exc_info_cooldown.value)

    # After cooldown expires, connection recovers
    await asyncio.sleep(0.25)

    mock_healthy_producer = AsyncMock()
    mock_healthy_producer.start = AsyncMock()
    mock_healthy_producer.send_and_wait = AsyncMock()

    with patch("app.adapters.kafka.AIOKafkaProducer", return_value=mock_healthy_producer):
        await adapter.publish("test-topic", b"key", b"val")
        assert adapter._state == ProducerState.RUNNING
        assert await adapter.is_healthy() is True


@pytest.mark.asyncio
async def test_aiokafka_producer_adapter_concurrent_start():
    from app.adapters.kafka import AIOKafkaProducerAdapter, ProducerState

    adapter = AIOKafkaProducerAdapter(
        bootstrap_servers="mock:9092",
        timeout_seconds=1.0,
        connect_timeout_seconds=1.0,
    )

    start_calls = 0

    async def mock_start():
        nonlocal start_calls
        start_calls += 1
        await asyncio.sleep(0.05)

    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock(side_effect=mock_start)
    mock_producer.send_and_wait = AsyncMock()

    with patch("app.adapters.kafka.AIOKafkaProducer", return_value=mock_producer):
        # Fire 5 concurrent publishes
        results = await asyncio.gather(
            adapter.publish("t", b"k1", b"v1"),
            adapter.publish("t", b"k2", b"v2"),
            adapter.publish("t", b"k3", b"v3"),
            adapter.publish("t", b"k4", b"v4"),
            adapter.publish("t", b"k5", b"v5"),
        )

    assert start_calls == 1
    assert adapter._state == ProducerState.RUNNING
    assert mock_producer.send_and_wait.call_count == 5


@pytest.mark.asyncio
async def test_aiokafka_producer_adapter_mid_run_failure():
    from app.adapters.kafka import AIOKafkaProducerAdapter, KafkaPublishError, ProducerState

    adapter = AIOKafkaProducerAdapter(
        bootstrap_servers="mock:9092",
        timeout_seconds=0.5,
        connect_timeout_seconds=0.5,
        reconnect_cooldown_seconds=0.1,
    )

    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock()
    mock_producer.send_and_wait = AsyncMock(side_effect=ConnectionResetError("Broker dropped"))

    with patch("app.adapters.kafka.AIOKafkaProducer", return_value=mock_producer):
        await adapter.start()
        assert adapter._state == ProducerState.RUNNING

        with pytest.raises(KafkaPublishError) as exc_info:
            await adapter.publish("topic", b"k", b"v")
        assert "Kafka publish failed" in str(exc_info.value)
        assert adapter._state == ProducerState.FAILED
        assert await adapter.is_healthy() is False


@pytest.mark.asyncio
async def test_aiokafka_producer_adapter_stop_when_never_started():
    from app.adapters.kafka import AIOKafkaProducerAdapter, ProducerState

    adapter = AIOKafkaProducerAdapter(bootstrap_servers="mock:9092")
    assert adapter._state == ProducerState.STOPPED
    # Should not raise
    await adapter.stop()
    assert adapter._state == ProducerState.STOPPED

