import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.adapters.kafka import FakeKafkaProducer
from app.adapters.key_resolver import FakeProjectKeyResolver


@pytest.mark.asyncio
async def test_ingest_performance_batch_happy_path_202(
    client: AsyncClient,
    test_project_api_key: str,
    fake_kafka: FakeKafkaProducer,
):
    batch_id = str(uuid.uuid4())
    payload = {
        "batch_id": batch_id,
        "environment": "production",
        "release": "1.8.0",
        "interval_start": "2026-10-13T10:00:00Z",
        "interval_end": "2026-10-13T10:00:10Z",
        "metrics": [
            {
                "route": "/payments",
                "method": "POST",
                "request_count": 100,
                "error_count": 5,
                "status_counts": {
                    "200": 90,
                    "404": 5,
                    "500": 5,
                },
                "latency_histogram": {
                    "le_100ms": 20,
                    "le_300ms": 50,
                    "le_1s": 25,
                    "gt_1s": 5,
                },
            }
        ],
    }

    response = await client.post(
        "/api/v1/ingest/performance",
        json=payload,
        headers={"X-Project-Key": test_project_api_key},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["accepted"] is True
    assert data["batch_id"] == batch_id

    # Verify message was published to Kafka topic
    assert len(fake_kafka.published_messages) == 1
    topic, key, val = fake_kafka.published_messages[0]
    assert topic == "performance-metrics"
    assert key is not None
    assert str(batch_id) in val.decode("utf-8")


@pytest.mark.asyncio
async def test_ingest_performance_batch_missing_key_401(client: AsyncClient):
    payload = {
        "batch_id": str(uuid.uuid4()),
        "interval_start": "2026-10-13T10:00:00Z",
        "interval_end": "2026-10-13T10:00:10Z",
        "metrics": [],
    }

    response = await client.post("/api/v1/ingest/performance", json=payload)
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_ingest_performance_batch_invalid_key_401(
    client: AsyncClient,
    fake_resolver: FakeProjectKeyResolver,
):
    fake_resolver.force_invalid = True
    payload = {
        "batch_id": str(uuid.uuid4()),
        "interval_start": "2026-10-13T10:00:00Z",
        "interval_end": "2026-10-13T10:00:10Z",
        "metrics": [],
    }

    response = await client.post(
        "/api/v1/ingest/performance",
        json=payload,
        headers={"X-Project-Key": "invalid_key"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_performance_batch_invalid_uuid_422(
    client: AsyncClient,
    test_project_api_key: str,
):
    payload = {
        "batch_id": "not-a-valid-uuid",
        "interval_start": "2026-10-13T10:00:00Z",
        "interval_end": "2026-10-13T10:00:10Z",
        "metrics": [],
    }

    response = await client.post(
        "/api/v1/ingest/performance",
        json=payload,
        headers={"X-Project-Key": test_project_api_key},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_performance_batch_negative_counts_422(
    client: AsyncClient,
    test_project_api_key: str,
):
    payload = {
        "batch_id": str(uuid.uuid4()),
        "interval_start": "2026-10-13T10:00:00Z",
        "interval_end": "2026-10-13T10:00:10Z",
        "metrics": [
            {
                "route": "/test",
                "method": "GET",
                "request_count": -1,
                "error_count": 0,
            }
        ],
    }

    response = await client.post(
        "/api/v1/ingest/performance",
        json=payload,
        headers={"X-Project-Key": test_project_api_key},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_performance_batch_supports_xfaultlinekey(
    client: AsyncClient,
    test_project_api_key: str,
):
    batch_id = str(uuid.uuid4())
    payload = {
        "batch_id": batch_id,
        "interval_start": "2026-10-13T10:00:00Z",
        "interval_end": "2026-10-13T10:00:10Z",
        "metrics": [],
    }

    response = await client.post(
        "/api/v1/ingest/performance",
        json=payload,
        headers={"X-Faultline-Key": test_project_api_key},
    )
    assert response.status_code == 202
    assert response.json()["batch_id"] == batch_id


@pytest.mark.asyncio
async def test_ingest_performance_batch_kafka_failure_returns_503(
    client: AsyncClient,
    test_project_api_key: str,
    fake_kafka: FakeKafkaProducer,
):
    fake_kafka.should_fail = True
    payload = {
        "batch_id": str(uuid.uuid4()),
        "interval_start": "2026-10-13T10:00:00Z",
        "interval_end": "2026-10-13T10:00:10Z",
        "metrics": [],
    }

    response = await client.post(
        "/api/v1/ingest/performance",
        json=payload,
        headers={"X-Project-Key": test_project_api_key},
    )
    assert response.status_code == 503
    assert response.headers.get("Retry-After") == "5"
    assert response.json()["detail"] == "Event could not be queued"

