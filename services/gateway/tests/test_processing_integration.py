import uuid
import pytest
import httpx
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.main import create_app
from app.middleware.rate_limit import MemoryRateLimiter


def create_mock_processing_app() -> FastAPI:
    """Mock Processing API simulating exact endpoint and auth behavior."""
    proc_app = FastAPI()

    @proc_app.get("/api/v1/projects/{project_id}/issues")
    async def list_issues(
        project_id: uuid.UUID,
        authorization: str | None = Header(default=None),
    ):
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        if authorization == "Bearer valid-token":
            return {
                "items": [{"id": str(uuid.uuid4()), "title": "IndexError", "status": "unresolved"}],
                "cursor": None,
            }
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return proc_app


@pytest.mark.asyncio
async def test_processing_endpoint_via_gateway_auth_behavior():
    """Verify that calling a Processing endpoint through the gateway:
    1. Returns 401 from upstream when token is missing or invalid.
    2. Returns 200 with identical body when token is valid.
    """
    processing_app = create_mock_processing_app()
    processing_transport = httpx.ASGITransport(app=processing_app)

    async def mock_network_dispatch(request: httpx.Request) -> httpx.Response:
        if "processing-api" in str(request.url):
            sub_req = httpx.Request(
                method=request.method,
                url=f"http://test{request.url.path}" + (f"?{request.url.query.decode()}" if request.url.query else ""),
                headers=request.headers,
                content=request.read(),
            )
            return await processing_transport.handle_async_request(sub_req)
        return httpx.Response(status_code=404, json={"detail": "not found"})

    settings = Settings(
        upstream_processing_url="http://processing-api:8002",
        rate_limit_strategy="memory",
    )
    gateway_app = create_app(custom_settings=settings)
    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_network_dispatch))
    gateway_app.state.http_client = mock_client
    gateway_app.state.rate_limiter = MemoryRateLimiter(limit=100, window_seconds=60)

    test_project_id = uuid.uuid4()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway_app), base_url="http://test") as client:
        # 1. No token -> Upstream 401
        resp_no_token = await client.get(f"/api/v1/projects/{test_project_id}/issues")
        assert resp_no_token.status_code == 401
        assert resp_no_token.json() == {"detail": "Missing or invalid credentials"}
        assert resp_no_token.headers.get("WWW-Authenticate") == "Bearer"

        # 2. Invalid token -> Upstream 401
        resp_bad_token = await client.get(
            f"/api/v1/projects/{test_project_id}/issues",
            headers={"Authorization": "Bearer bad-token"},
        )
        assert resp_bad_token.status_code == 401
        assert resp_bad_token.json() == {"detail": "Missing or invalid credentials"}

        # 3. Valid token -> Upstream 200 with issues list
        resp_valid = await client.get(
            f"/api/v1/projects/{test_project_id}/issues",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert resp_valid.status_code == 200
        data = resp_valid.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "IndexError"

    await mock_client.aclose()
