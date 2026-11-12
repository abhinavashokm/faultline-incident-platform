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
    status_counts: dict | None = ...,  # sentinel to allow passing None explicitly
    latency_histogram: list[int] | None = None,
    histogram_version: int = 1,
) -> None:
    if latency_histogram is None:
        latency_histogram = [50, 30, 10, 5, 3, 2]
    if status_counts is ...:
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
        f"/api/v1/projects/{test_project_id}/performance/endpoint-detail",
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
        f"/api/v1/projects/{test_project_id}/performance/endpoint-detail",
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
        f"/api/v1/projects/{test_project_id}/performance/endpoint-detail",
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
        f"/api/v1/projects/{test_project_id}/performance/endpoint-detail",
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
        f"/api/v1/projects/{test_project_id}/performance/endpoint-detail",
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
        f"/api/v1/projects/{test_project_id}/performance/endpoint-detail",
        params={
            "route": "/anything",
            "method": "GET",
            "from": from_time,
            "to": to_time,
        },
    )
    assert res_detail.status_code == 401


@pytest.mark.asyncio
async def test_performance_filters_endpoint(
    client: AsyncClient,
    test_project_id: uuid.UUID,
) -> None:
    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/filters",
    )
    assert response.status_code == 200
    data = response.json()
    assert "environments" in data
    assert "releases" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_performance_summary_happy_path_and_filters(
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
        route_template="/api/items",
        http_method="GET",
        environment="staging",
        release="v1.0.0",
        bucket_start=now,
        request_count=1000,
        error_count=50,
        latency_histogram=[400, 300, 200, 50, 30, 20],
    )
    await insert_bucket(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        route_template="/api/checkout",
        http_method="POST",
        environment="production",
        release="v1.1.0",
        bucket_start=now,
        request_count=500,
        error_count=10,
        latency_histogram=[100, 100, 100, 100, 50, 50],
    )

    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    # Overall summary (no filter)
    res_overall = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/summary",
        params={"from": from_time, "to": to_time},
    )
    assert res_overall.status_code == 200
    data_overall = res_overall.json()
    assert data_overall["request_count"] == 1500
    assert data_overall["error_count"] == 60
    assert data_overall["error_rate"] == 4.0
    assert data_overall["p50_ms"] is not None
    assert data_overall["p95_ms"] is not None
    assert data_overall["p99_ms"] is not None

    # Filter by route and method
    res_filtered = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/summary",
        params={
            "from": from_time,
            "to": to_time,
            "route": "/api/items",
            "method": "get ",  # test trimming and uppercase normalization
        },
    )
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()
    assert data_filtered["request_count"] == 1000
    assert data_filtered["error_count"] == 50
    assert data_filtered["error_rate"] == 5.0


@pytest.mark.asyncio
async def test_performance_summary_and_timeseries_validation(
    client: AsyncClient,
    test_project_id: uuid.UUID,
) -> None:
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    # Route without method -> 422
    res_no_method = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/summary",
        params={"from": from_time, "to": to_time, "route": "/api/users"},
    )
    assert res_no_method.status_code == 422
    assert res_no_method.json()["detail"][0]["field"] == "method"

    # Method without route -> 422
    res_no_route = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/summary",
        params={"from": from_time, "to": to_time, "method": "GET"},
    )
    assert res_no_route.status_code == 422
    assert res_no_route.json()["detail"][0]["field"] == "route"

    # Same for timeseries: route without method -> 422
    res_ts_no_method = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/timeseries",
        params={"from": from_time, "to": to_time, "route": "/api/users"},
    )
    assert res_ts_no_method.status_code == 422

    # Same for timeseries: method without route -> 422
    res_ts_no_route = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/timeseries",
        params={"from": from_time, "to": to_time, "method": "GET"},
    )
    assert res_ts_no_route.status_code == 422

    # Bad time range: from >= to -> 422
    res_bad_range = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/summary",
        params={"from": to_time, "to": from_time},
    )
    assert res_bad_range.status_code == 422


@pytest.mark.asyncio
async def test_performance_timeseries_happy_path(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
) -> None:
    # 1 hour window -> interval should be 60 seconds
    base_time = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    t1 = base_time + timedelta(minutes=5)
    await insert_bucket(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        route_template="/test/ts",
        http_method="GET",
        bucket_start=t1,
        request_count=100,
        error_count=2,
        latency_histogram=[80, 10, 5, 3, 2, 0],
    )

    from_time = base_time.isoformat()
    to_time = (base_time + timedelta(minutes=10)).isoformat()

    response = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/timeseries",
        params={"from": from_time, "to": to_time},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["interval_seconds"] == 60
    assert len(data["points"]) == 10  # 10 1-minute buckets

    # Find the bucket at t1
    matching_points = [p for p in data["points"] if p["t"] == t1.strftime("%Y-%m-%dT%H:%M:%SZ")]
    assert len(matching_points) == 1
    pt = matching_points[0]
    assert pt["requests"] == 100
    assert pt["error_rate"] == 2.0
    assert pt["p95_ms"] is not None

    # Empty buckets should have requests=0 and null error_rate/p95_ms
    empty_points = [p for p in data["points"] if p["requests"] == 0]
    assert len(empty_points) == 9
    assert empty_points[0]["error_rate"] is None
    assert empty_points[0]["p95_ms"] is None


@pytest.mark.asyncio
async def test_workspace_isolation_summary_and_timeseries(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_project_id: uuid.UUID,
) -> None:
    # Insert for other workspace
    other_workspace_id = uuid.uuid4()
    now = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
    await insert_bucket(
        session_factory,
        workspace_id=other_workspace_id,
        project_id=test_project_id,
        route_template="/secret",
        http_method="GET",
        bucket_start=now,
    )

    from_time = (now - timedelta(hours=1)).isoformat()
    to_time = (now + timedelta(hours=1)).isoformat()

    # Summary should return 404
    res_summary = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/summary",
        params={"from": from_time, "to": to_time},
    )
    assert res_summary.status_code == 404

    # Timeseries should return 404
    res_timeseries = await client.get(
        f"/api/v1/projects/{test_project_id}/performance/timeseries",
        params={"from": from_time, "to": to_time},
    )
    assert res_timeseries.status_code == 404

