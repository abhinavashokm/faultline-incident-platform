from datetime import datetime, timezone
import json
import uuid
import pytest
from httpx import AsyncClient

from app.adapters.kafka import FakeKafkaProducer
from app.adapters.key_resolver import FakeProjectKeyResolver
from app.adapters.redis_limiter import FakeRateLimiter


@pytest.mark.asyncio
async def test_ingest_event_happy_path_202(
    client: AsyncClient,
    fake_kafka: FakeKafkaProducer,
    test_public_key: str,
    test_project_id: uuid.UUID,
    test_workspace_id: uuid.UUID,
):
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "ZeroDivisionError",
        "message": "division by zero",
        "service": "billing-service",
        "environment": "production",
        "release": "v1.2.0",
        "http_method": "post",
        "status_code": 500,
        "context": {
            "user": "bob",
            "authorization": "sensitive-token-to-scrub",
        },
    }

    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": test_public_key},
    )

    assert response.status_code == 202
    res_data = response.json()
    assert res_data["status"] == "accepted"
    assert res_data["event_id"] == event_id
    assert "X-Request-ID" in response.headers

    # Verify message published to Kafka
    assert len(fake_kafka.published_messages) == 1
    topic, key, value = fake_kafka.published_messages[0]
    assert topic == "error-events"
    assert key == str(test_project_id).encode("utf-8")

    envelope = json.loads(value.decode("utf-8"))
    assert envelope["schema_version"] == 1
    assert envelope["event_id"] == event_id
    assert envelope["project_id"] == str(test_project_id)
    assert envelope["workspace_id"] == str(test_workspace_id)
    assert envelope["received_at"] is not None
    assert envelope["payload"]["http_method"] == "POST"
    assert envelope["payload"]["context"]["authorization"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_client_supplied_project_id_is_ignored(
    client: AsyncClient,
    fake_kafka: FakeKafkaProducer,
    test_public_key: str,
    test_project_id: uuid.UUID,
    test_workspace_id: uuid.UUID,
):
    spoofed_project_id = str(uuid.uuid4())
    spoofed_workspace_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())

    payload = {
        "event_id": event_id,
        "project_id": spoofed_project_id,
        "workspace_id": spoofed_workspace_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "SecurityTestError",
        "message": "spoofing test",
    }

    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": test_public_key},
    )

    assert response.status_code == 202

    # Verify that Kafka envelope uses server-derived IDs, not the spoofed ones
    topic, key, value = fake_kafka.published_messages[0]
    envelope = json.loads(value.decode("utf-8"))
    assert envelope["project_id"] == str(test_project_id)
    assert envelope["workspace_id"] == str(test_workspace_id)
    assert envelope["project_id"] != spoofed_project_id
    assert envelope["workspace_id"] != spoofed_workspace_id


@pytest.mark.asyncio
async def test_auth_failure_missing_or_bad_key(client: AsyncClient):
    payload = {
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "ValueError",
    }

    # Missing header -> 401
    resp_missing = await client.post("/api/v1/events", json=payload)
    assert resp_missing.status_code == 401
    assert "detail" in resp_missing.json()

    # Invalid key -> 401
    resp_invalid = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": "invalid_unknown_key"},
    )
    assert resp_invalid.status_code == 401
    assert "detail" in resp_invalid.json()


@pytest.mark.asyncio
async def test_auth_failure_revoked_key(
    client: AsyncClient,
    fake_resolver: FakeProjectKeyResolver,
):
    revoked_key = "fl_pub_revoked9999"
    fake_resolver.add_key(
        revoked_key,
        project_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        revoked=True,
    )

    payload = {
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "ValueError",
    }

    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": revoked_key},
    )
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_schema_validation_error_422(
    client: AsyncClient,
    test_public_key: str,
):
    # Missing required field occurred_at
    payload = {
        "event_id": str(uuid.uuid4()),
        "exception_type": "ValueError",
    }

    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": test_public_key},
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_payload_too_large_413(
    client: AsyncClient,
    test_public_key: str,
):
    # Request body exceeding 200 KB
    huge_message = "x" * (250 * 1024)
    payload = {
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "ValueError",
        "message": huge_message,
    }

    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": test_public_key},
    )
    assert response.status_code == 413
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_rate_limit_exceeded_429(
    client: AsyncClient,
    test_public_key: str,
    fake_limiter: FakeRateLimiter,
):
    fake_limiter.force_block = True

    payload = {
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "ValueError",
    }

    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": test_public_key},
    )
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "60"
    assert "Rate limit exceeded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_kafka_failure_returns_503(
    client: AsyncClient,
    test_public_key: str,
    fake_kafka: FakeKafkaProducer,
):
    fake_kafka.should_fail = True

    payload = {
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "RuntimeError",
    }

    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": test_public_key},
    )
    assert response.status_code == 503
    assert "Retry-After" in response.headers
    assert response.json()["detail"] == "Event could not be queued"


@pytest.mark.asyncio
async def test_resolver_down_and_cold_cache_returns_503(
    client: AsyncClient,
    fake_resolver: FakeProjectKeyResolver,
    test_public_key: str,
):
    fake_resolver.simulate_unreachable = True

    payload = {
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "RuntimeError",
    }

    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Faultline-Key": test_public_key},
    )
    assert response.status_code == 503
    assert "Retry-After" in response.headers
    assert "Key resolution service unavailable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_backpressure_saturation_returns_503(
    fake_kafka: FakeKafkaProducer,
    fake_limiter: FakeRateLimiter,
    fake_resolver: FakeProjectKeyResolver,
    test_public_key: str,
):
    import asyncio
    from httpx import ASGITransport
    from app.dependencies import (
        get_concurrency_semaphore,
        get_kafka_producer,
        get_key_resolver,
        get_rate_limiter,
    )
    from app.main import create_app

    app = create_app()
    # Saturate semaphore by setting value to 0 and acquiring
    semaphore = asyncio.Semaphore(1)
    await semaphore.acquire()

    app.dependency_overrides[get_kafka_producer] = lambda: fake_kafka
    app.dependency_overrides[get_rate_limiter] = lambda: fake_limiter
    app.dependency_overrides[get_key_resolver] = lambda: fake_resolver
    app.dependency_overrides[get_concurrency_semaphore] = lambda: semaphore

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "event_id": str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "exception_type": "BackpressureError",
        }
        response = await ac.post(
            "/api/v1/events",
            json=payload,
            headers={"X-Faultline-Key": test_public_key},
        )
        assert response.status_code == 503
        assert "Retry-After" in response.headers
        assert "maximum concurrent requests" in response.json()["detail"]


@pytest.mark.asyncio
async def test_header_fallbacks(
    client: AsyncClient,
    test_public_key: str,
):
    payload = {
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "exception_type": "FallbackTestError",
    }

    # 1. Fallback via X-Project-Key
    resp1 = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"X-Project-Key": test_public_key},
    )
    assert resp1.status_code == 202

    # 2. Fallback via Authorization Bearer
    payload["event_id"] = str(uuid.uuid4())
    resp2 = await client.post(
        "/api/v1/events",
        json=payload,
        headers={"Authorization": f"Bearer {test_public_key}"},
    )
    assert resp2.status_code == 202


@pytest.mark.asyncio
async def test_control_plane_error_mappings_through_api(fake_kafka, fake_limiter):
    import asyncio
    from unittest.mock import AsyncMock
    import httpx
    from httpx import ASGITransport
    from app.adapters.key_resolver import CachedHttpProjectKeyResolver
    from app.dependencies import (
        get_concurrency_semaphore,
        get_kafka_producer,
        get_key_resolver,
        get_rate_limiter,
    )
    from app.main import create_app

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cold cache
    mock_http = AsyncMock()

    key_resolver = CachedHttpProjectKeyResolver(
        redis_client=mock_redis,
        http_client=mock_http,
        control_plane_url="http://control-plane:8000",
        service_token="test-secret",
    )

    app = create_app()
    app.dependency_overrides[get_kafka_producer] = lambda: fake_kafka
    app.dependency_overrides[get_rate_limiter] = lambda: fake_limiter
    app.dependency_overrides[get_key_resolver] = lambda: key_resolver
    app.dependency_overrides[get_concurrency_semaphore] = lambda: asyncio.Semaphore(100)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "event_id": str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "exception_type": "MappingTestError",
        }

        # 1. Control Plane 404 -> Ingestion 401
        mock_http.get.return_value = httpx.Response(404, json={"detail": "Project key not found"})
        resp = await ac.post("/api/v1/events", json=payload, headers={"X-Faultline-Key": "test-key-404"})
        assert resp.status_code == 401
        assert "Invalid or revoked project key" in resp.json()["detail"]

        # 2. Control Plane 401 -> Ingestion 503 + Retry-After
        mock_http.get.return_value = httpx.Response(401, json={"detail": "Missing or invalid service token"})
        resp = await ac.post("/api/v1/events", json=payload, headers={"X-Faultline-Key": "test-key-401"})
        assert resp.status_code == 503
        assert resp.headers.get("Retry-After") == "5"

        # 3. Control Plane 403 -> Ingestion 503 + Retry-After
        mock_http.get.return_value = httpx.Response(403, json={"detail": "Forbidden"})
        resp = await ac.post("/api/v1/events", json=payload, headers={"X-Faultline-Key": "test-key-403"})
        assert resp.status_code == 503
        assert resp.headers.get("Retry-After") == "5"

        # 4. Control Plane 500 -> Ingestion 503 + Retry-After
        mock_http.get.return_value = httpx.Response(500, text="Internal Server Error")
        resp = await ac.post("/api/v1/events", json=payload, headers={"X-Faultline-Key": "test-key-500"})
        assert resp.status_code == 503
        assert resp.headers.get("Retry-After") == "5"

        # 5. Connection Error -> Ingestion 503 + Retry-After
        mock_http.get.side_effect = httpx.ConnectError("Failed to connect")
        resp = await ac.post("/api/v1/events", json=payload, headers={"X-Faultline-Key": "test-key-conn"})
        assert resp.status_code == 503
        assert resp.headers.get("Retry-After") == "5"

