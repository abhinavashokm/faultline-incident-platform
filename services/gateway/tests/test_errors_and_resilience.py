import pytest
import httpx
from tests.conftest import MockUpstreamState


@pytest.mark.asyncio
async def test_upstream_connection_error_returns_502(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    mock_upstream.exception_to_raise = httpx.ConnectError(
        "Connection refused to internal service http://control-plane:8000"
    )

    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 502
    data = resp.json()

    # Exact sanitized error response
    assert data == {"detail": "Upstream unavailable"}
    # Never leak internal URLs or exception text to client
    assert "control-plane" not in resp.text
    assert "refused" not in resp.text
    # Request ID present
    assert resp.headers.get("X-Request-ID") is not None


@pytest.mark.asyncio
async def test_upstream_timeout_returns_504(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    mock_upstream.exception_to_raise = httpx.ReadTimeout(
        "Read timed out from http://processing-api:8002"
    )

    resp = await client.get("/api/v1/projects/550e8400-e29b-41d4-a716-446655440000/issues")
    assert resp.status_code == 504
    data = resp.json()

    # Exact sanitized error response
    assert data == {"detail": "Upstream timeout"}
    # Never leak internal URLs or exception text
    assert "processing-api" not in resp.text
    assert "timed out" not in resp.text
    assert resp.headers.get("X-Request-ID") is not None

