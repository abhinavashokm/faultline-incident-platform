import base64
from datetime import datetime, timedelta, timezone
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from faultline_auth import Principal, get_principal
from app.main import create_app
from app.perf.models import MetricBucket


async def insert_bucket(
    session_factory: async_sessionmaker[AsyncSession],
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    route_template: str,
    http_method: str,
    bucket_start: datetime,
    environment: str = "production",
    service: str = "",
    release: str = "v1.0.0",
    request_count: int = 100,
    error_count: int = 5,
    status_counts: dict | None = None,
    latency_histogram: list[int] | None = None,
    histogram_version: int = 1,
) -> None:
    if latency_histogram is None:
        latency_histogram = [50, 30, 10, 5, 3, 2]
    if status_counts is None:
        status_counts = {"200": 95, "500": 5}

    async with session_factory() as session:
        bucket = MetricBucket(
            workspace_id=workspace_id,
            project_id=project_id,
            environment=environment,
            service=service,
            route_template=route_template,
            http_method=http_method,
            release=release,
            bucket_start=bucket_start,
            request_count=request_count,
            error_count=error_count,
            status_counts=status_counts,
            latency_histogram=latency_histogram,
            histogram_version=histogram_version,
        )
        session.add(bucket)
        await session.commit()


@pytest.mark.asyncio
async def test_list_endpoints_happy_path(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    # Endpoint 1: /payments POST (higher latency)
    await insert_bucket(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        route_template="/payments",
        http_method="POST",
        bucket_start=now,
        request_count=100,
        error_count=4,
        latency_histogram=[0, 0, 0, 0, 0, 100],  # All overflow -> p95 = 1000
    )
    # Endpoint 2: /users GET (lower latency)
    await insert_bucket(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        route_template="/users",
        http_method="GET",
        bucket_start=now,
        request_count=200,
        error_count=2,
        latency_histogram=[200, 0, 0, 0, 0, 0],  # All in bucket 0 [0, 50] -> p95 ~ 48
    )

    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoints",
        params={"from": from_time, "to": to_time},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["truncated"] is False
    assert len(data["items"]) == 2

    # Check sorting: p95 desc -> /payments first
    assert data["items"][0]["route"] == "/payments"
    assert data["items"][0]["method"] == "POST"
    assert data["items"][0]["p95_ms"] == 1000
    assert data["items"][0]["error_rate"] == 4.0

    assert data["items"][1]["route"] == "/users"
    assert data["items"][1]["method"] == "GET"
    assert data["items"][1]["p95_ms"] == 48


@pytest.mark.asyncio
async def test_list_endpoints_empty(
    client: AsyncClient,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoints",
        params={"from": from_time, "to": to_time},
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {"items": [], "total": 0, "truncated": False}


@pytest.mark.asyncio
async def test_list_endpoints_validation_errors(
    client: AsyncClient,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)

    # from >= to
    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoints",
        params={"from": now.isoformat(), "to": now.isoformat()},
    )
    assert response.status_code == 422
    assert "greater than from" in response.json()["detail"][0]["message"]

    # Range > 7 days
    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoints",
        params={
            "from": now.isoformat(),
            "to": (now + timedelta(days=7, seconds=1)).isoformat(),
        },
    )
    assert response.status_code == 422
    assert "exceed 7 days" in response.json()["detail"][0]["message"]


@pytest.mark.asyncio
async def test_endpoint_detail_missing_params(
    client: AsyncClient,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    # Missing route and method
    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoint",
        params={
            "from": now.isoformat(),
            "to": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 422
    fields = [err["loc"][-1] for err in response.json()["detail"]]
    assert "route" in fields
    assert "method" in fields


@pytest.mark.asyncio
async def test_endpoint_detail_not_found(
    client: AsyncClient,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoint",
        params={
            "route": "/missing",
            "method": "GET",
            "from": now.isoformat(),
            "to": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Endpoint not found"}


@pytest.mark.asyncio
async def test_endpoint_detail_happy_path_and_null_status_counts(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    # Row 1 with status counts and release v1.0.0
    await insert_bucket(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        route_template="/orders/{id}",
        http_method="GET",
        release="v1.0.0",
        bucket_start=now,
        request_count=100,
        error_count=2,
        status_counts={"200": 98, "500": 2},
        latency_histogram=[40, 30, 15, 10, 4, 1],
    )
    # Row 2 with NULL status_counts and release v1.1.0 (to verify lateral unnest skips NULL)
    await insert_bucket(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        route_template="/orders/{id}",
        http_method="GET",
        release="v1.1.0",
        bucket_start=now + timedelta(minutes=1),
        request_count=50,
        error_count=0,
        status_counts=None,
        latency_histogram=[50, 0, 0, 0, 0, 0],
    )

    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoint",
        params={
            "route": "/orders/{id}",
            "method": "GET",
            "from": from_time,
            "to": to_time,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Total requests = 150, errors = 2
    assert data["summary"]["request_count"] == 150
    assert data["summary"]["error_rate"] == 1.33
    assert data["summary"]["p50_ms"] is not None

    # Latency distribution (6 buckets)
    assert len(data["latency_distribution"]) == 6
    assert data["latency_distribution"][0]["le_ms"] == 50
    assert data["latency_distribution"][0]["count"] == 90
    assert data["latency_distribution"][5]["le_ms"] is None
    assert data["latency_distribution"][5]["count"] == 1

    # Status counts: null row skipped gracefully, only row 1 counted
    assert data["status_counts"] == {"200": 98, "500": 2}

    # Releases: 2 entries sorted asc
    assert len(data["releases"]) == 2
    assert data["releases"][0]["release"] == "v1.0.0"
    assert data["releases"][0]["requests"] == 100
    assert data["releases"][1]["release"] == "v1.1.0"
    assert data["releases"][1]["requests"] == 50


@pytest.mark.asyncio
async def test_endpoint_detail_release_filter_isolation(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    await insert_bucket(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        route_template="/search",
        http_method="GET",
        release="v1.0.0",
        bucket_start=now,
        request_count=100,
        error_count=5,
    )
    await insert_bucket(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        route_template="/search",
        http_method="GET",
        release="v2.0.0",
        bucket_start=now + timedelta(minutes=1),
        request_count=200,
        error_count=10,
    )

    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    # Filter with release=v1.0.0
    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoint",
        params={
            "route": "/search",
            "method": "GET",
            "from": from_time,
            "to": to_time,
            "release": "v1.0.0",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Summary respects release filter -> only 100 requests
    assert data["summary"]["request_count"] == 100

    # Releases section IGNORES release filter -> contains both v1.0.0 and v2.0.0
    releases = [r["release"] for r in data["releases"]]
    assert "v1.0.0" in releases
    assert "v2.0.0" in releases
    assert len(data["releases"]) == 2


@pytest.mark.asyncio
async def test_workspace_isolation(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    foreign_workspace_id = uuid.uuid4()

    # Insert data belonging to another workspace for the same project_id
    await insert_bucket(
        session_factory,
        workspace_id=foreign_workspace_id,
        project_id=test_project_id,
        route_template="/secret",
        http_method="GET",
        bucket_start=now,
        request_count=100,
    )

    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    # List endpoint should return empty
    res_list = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoints",
        params={"from": from_time, "to": to_time},
    )
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 0

    # Detail endpoint should return 404
    res_detail = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoint",
        params={
            "route": "/secret",
            "method": "GET",
            "from": from_time,
            "to": to_time,
        },
    )
    assert res_detail.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request_fails(
    unauth_client: AsyncClient,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    res_list = await unauth_client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoints",
        params={"from": from_time, "to": to_time},
    )
    assert res_list.status_code == 401

    res_detail = await unauth_client.get(
        f"/api/v1/projects/{test_project_id}/performance/endpoint",
        params={
            "route": "/anything",
            "method": "GET",
            "from": from_time,
            "to": to_time,
        },
    )
    assert res_detail.status_code == 401
