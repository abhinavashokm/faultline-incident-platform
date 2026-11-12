import uuid

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.histograms import HISTOGRAM_BUCKETS
from app.schemas.performance import PerformanceBatchIngestRequest, RouteMetric


def test_v1_buckets():
    assert HISTOGRAM_BUCKETS[1] == [50, 100, 250, 500, 1000, float("inf")]


def test_validator_valid_payload():
    metric = RouteMetric(
        route="/api/v1/checkout",
        method="POST",
        request_count=10,
        error_count=0,
        histogram_version=1,
        latency_histogram=[1, 2, 3, 2, 1, 1],
    )
    assert metric.histogram_version == 1
    assert metric.latency_histogram == [1, 2, 3, 2, 1, 1]


def test_validator_unknown_version_fails():
    with pytest.raises(ValidationError) as exc_info:
        RouteMetric(
            route="/api/v1/checkout",
            method="POST",
            request_count=10,
            error_count=0,
            histogram_version=999,
            latency_histogram=[1, 2, 3, 2, 1, 1],
        )
    assert "histogram_version" in str(exc_info.value)
    assert "999" in str(exc_info.value)


def test_validator_wrong_length_fails():
    with pytest.raises(ValidationError) as exc_info:
        RouteMetric(
            route="/api/v1/checkout",
            method="POST",
            request_count=10,
            error_count=0,
            histogram_version=1,
            latency_histogram=[1, 2, 3],  # expected length 6
        )
    assert "does not match expected length" in str(exc_info.value)


def test_validator_negative_count_fails():
    with pytest.raises(ValidationError) as exc_info:
        RouteMetric(
            route="/api/v1/checkout",
            method="POST",
            request_count=10,
            error_count=0,
            histogram_version=1,
            latency_histogram=[1, 2, -3, 2, 1, 1],
        )
    assert "cannot be negative" in str(exc_info.value)


@pytest.mark.asyncio
async def test_endpoint_validation_http_422(
    client: AsyncClient,
    test_project_api_key: str,
):
    base_payload = {
        "batch_id": str(uuid.uuid4()),
        "interval_start": "2026-10-13T10:00:00Z",
        "interval_end": "2026-10-13T10:00:10Z",
    }

    # 1. Unknown version -> 422
    payload_bad_version = {
        **base_payload,
        "metrics": [
            {
                "route": "/test",
                "method": "GET",
                "request_count": 1,
                "error_count": 0,
                "histogram_version": 99,
                "latency_histogram": [1, 1, 1, 1, 1, 1],
            }
        ],
    }
    resp = await client.post(
        "/api/v1/ingest/performance",
        json=payload_bad_version,
        headers={"X-Project-Key": test_project_api_key},
    )
    assert resp.status_code == 422
    assert "histogram_version" in resp.text

    # 2. Wrong length -> 422
    payload_wrong_len = {
        **base_payload,
        "metrics": [
            {
                "route": "/test",
                "method": "GET",
                "request_count": 1,
                "error_count": 0,
                "histogram_version": 1,
                "latency_histogram": [1, 2],
            }
        ],
    }
    resp = await client.post(
        "/api/v1/ingest/performance",
        json=payload_wrong_len,
        headers={"X-Project-Key": test_project_api_key},
    )
    assert resp.status_code == 422
    assert "does not match expected length" in resp.text

    # 3. Negative count -> 422
    payload_negative = {
        **base_payload,
        "metrics": [
            {
                "route": "/test",
                "method": "GET",
                "request_count": 1,
                "error_count": 0,
                "histogram_version": 1,
                "latency_histogram": [1, -5, 1, 1, 1, 1],
            }
        ],
    }
    resp = await client.post(
        "/api/v1/ingest/performance",
        json=payload_negative,
        headers={"X-Project-Key": test_project_api_key},
    )
    assert resp.status_code == 422
    assert "cannot be negative" in resp.text

    # 4. Valid payload -> 202
    payload_valid = {
        **base_payload,
        "metrics": [
            {
                "route": "/test",
                "method": "GET",
                "request_count": 1,
                "error_count": 0,
                "histogram_version": 1,
                "latency_histogram": [1, 2, 3, 4, 5, 6],
            }
        ],
    }
    resp = await client.post(
        "/api/v1/ingest/performance",
        json=payload_valid,
        headers={"X-Project-Key": test_project_api_key},
    )
    assert resp.status_code == 202
