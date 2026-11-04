import pytest
import httpx
from tests.conftest import MockUpstreamState


@pytest.mark.asyncio
async def test_longest_prefix_routing_processing_vs_control_plane(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    project_id = "e5792472-e1a5-48b4-b816-773df4b99aa3"

    # 1. Processing route: /api/v1/projects/{project_id}/issues
    resp_issues = await client.get(f"/api/v1/projects/{project_id}/issues")
    assert resp_issues.status_code == 200
    last_req = mock_upstream.received_requests[-1]
    assert str(last_req.url) == f"http://processing-api:8002/api/v1/projects/{project_id}/issues"

    # 2. Control Plane route: /api/v1/projects/{project_id}
    resp_proj = await client.get(f"/api/v1/projects/{project_id}")
    assert resp_proj.status_code == 200
    last_req = mock_upstream.received_requests[-1]
    assert str(last_req.url) == f"http://control-plane:8000/api/v1/projects/{project_id}"

    # 3. Control Plane route: /api/v1/projects
    resp_list = await client.get("/api/v1/projects")
    assert resp_list.status_code == 200
    last_req = mock_upstream.received_requests[-1]
    assert str(last_req.url) == "http://control-plane:8000/api/v1/projects"


@pytest.mark.asyncio
async def test_routing_control_plane_endpoints(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    # Auth route
    resp = await client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "secret"})
    assert resp.status_code == 200
    assert str(mock_upstream.received_requests[-1].url) == "http://control-plane:8000/api/v1/auth/login"

    # JWKS route
    resp = await client.get("/.well-known/jwks.json")
    assert resp.status_code == 200
    assert str(mock_upstream.received_requests[-1].url) == "http://control-plane:8000/.well-known/jwks.json"

    # Workspaces route
    resp = await client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    assert str(mock_upstream.received_requests[-1].url) == "http://control-plane:8000/api/v1/workspaces"


@pytest.mark.asyncio
async def test_routing_ingestion_events(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    resp = await client.post(
        "/api/v1/events",
        json={"event_id": "123", "message": "error"},
        headers={"X-Faultline-Key": "fl_key_123"},
    )
    assert resp.status_code == 200
    assert str(mock_upstream.received_requests[-1].url) == "http://ingestion:8001/api/v1/events"


@pytest.mark.asyncio
async def test_unknown_path_returns_404(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    resp = await client.get("/api/v1/unknown-endpoint")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Not found"}
    # Never forwarded to upstream
    assert len(mock_upstream.received_requests) == 0


@pytest.mark.asyncio
async def test_prefix_isolation(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    # Path starts with /api/v1/auth, but is not a sub-path (/api/v1/authorization)
    resp = await client.get("/api/v1/authorization")
    assert resp.status_code == 404
    assert len(mock_upstream.received_requests) == 0


@pytest.mark.asyncio
async def test_query_params_preserved(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    resp = await client.get("/api/v1/projects?status=active&limit=10")
    assert resp.status_code == 200
    last_req = mock_upstream.received_requests[-1]
    assert str(last_req.url) == "http://control-plane:8000/api/v1/projects?status=active&limit=10"

