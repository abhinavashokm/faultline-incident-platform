import pytest
import httpx
from tests.conftest import MockUpstreamState


@pytest.mark.asyncio
async def test_health_endpoint_no_upstream_calls(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    # Assert no upstreams were called
    assert len(mock_upstream.received_requests) == 0


@pytest.mark.asyncio
async def test_health_upstreams_all_healthy(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    mock_upstream.response_status = 200

    resp = await client.get("/health/upstreams")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["upstreams"]["control-plane"] == "ok"
    assert data["upstreams"]["ingestion"] == "ok"
    assert data["upstreams"]["processing"] == "ok"


@pytest.mark.asyncio
async def test_health_upstreams_degraded(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    def custom_handler(req: httpx.Request) -> httpx.Response:
        if "processing" in str(req.url):
            raise httpx.ConnectError("Connection refused")
        return httpx.Response(status_code=200, json={"status": "ok"})

    mock_upstream.custom_handler = custom_handler

    resp = await client.get("/health/upstreams")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["upstreams"]["control-plane"] == "ok"
    assert data["upstreams"]["ingestion"] == "ok"
    assert data["upstreams"]["processing"] == "unavailable"
    # Never leaks internal exception text
    assert "refused" not in resp.text

