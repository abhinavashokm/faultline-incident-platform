import pytest
import httpx
from tests.conftest import MockUpstreamState


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, _ = app_with_mock

    # Allowed origin: http://localhost:3000
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type, X-Request-ID",
    }
    resp = await client.options("/api/v1/projects", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"
    assert "x-request-id" in resp.headers.get("access-control-allow-headers", "").lower()
    assert "post" in resp.headers.get("access-control-allow-methods", "").lower()


@pytest.mark.asyncio
async def test_cors_actual_request_exposes_request_id(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, _ = app_with_mock

    resp = await client.get("/api/v1/projects", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "x-request-id" in resp.headers.get("access-control-expose-headers", "").lower()


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_origin(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, _ = app_with_mock

    # Disallowed origin
    headers = {
        "Origin": "http://evil-site.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization",
    }
    resp = await client.options("/api/v1/projects", headers=headers)
    # CORS middleware does not set Access-Control-Allow-Origin for unauthorized origin
    assert "access-control-allow-origin" not in resp.headers
