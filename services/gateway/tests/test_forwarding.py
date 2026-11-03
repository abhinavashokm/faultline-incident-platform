import pytest
import httpx
from tests.conftest import MockUpstreamState


@pytest.mark.asyncio
async def test_credentials_forwarded_unchanged(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    auth_header = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.dummy.sig"
    sdk_key = "fl_live_abcdef1234567890"
    project_key = "proj_key_0987654321"

    resp = await client.get(
        "/api/v1/projects",
        headers={
            "Authorization": auth_header,
            "X-Faultline-Key": sdk_key,
            "X-Project-Key": project_key,
        },
    )
    assert resp.status_code == 200
    last_req = mock_upstream.received_requests[-1]
    assert last_req.headers.get("authorization") == auth_header
    assert last_req.headers.get("x-faultline-key") == sdk_key
    assert last_req.headers.get("x-project-key") == project_key


@pytest.mark.asyncio
async def test_spoofed_identity_headers_are_stripped(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    resp = await client.get(
        "/api/v1/projects",
        headers={
            "X-User-Id": "attacker-user-id",
            "X-Workspace-Id": "attacker-workspace-id",
            "X-Principal-User": "attacker-principal",
            "X-Principal-Role": "admin",
            "X-Principal": "root",
            "X-Forwarded-User": "admin",
            "X-Role": "superadmin",
            "Authorization": "Bearer legitimate-token",
        },
    )
    assert resp.status_code == 200
    last_req = mock_upstream.received_requests[-1]

    # Verify all spoofed identity headers are stripped
    assert "x-user-id" not in last_req.headers
    assert "x-workspace-id" not in last_req.headers
    assert "x-principal-user" not in last_req.headers
    assert "x-principal-role" not in last_req.headers
    assert "x-principal" not in last_req.headers
    assert "x-forwarded-user" not in last_req.headers
    assert "x-role" not in last_req.headers

    # Authorization preserved
    assert last_req.headers.get("authorization") == "Bearer legitimate-token"


@pytest.mark.asyncio
async def test_hop_by_hop_headers_stripped(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    resp = await client.get(
        "/api/v1/projects",
        headers={
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=5",
            "Proxy-Authenticate": "basic",
            "Proxy-Authorization": "dummy",
            "TE": "trailers",
            "Upgrade": "websocket",
        },
    )
    assert resp.status_code == 200
    last_req = mock_upstream.received_requests[-1]

    assert "keep-alive" not in last_req.headers
    assert "proxy-authenticate" not in last_req.headers
    assert "proxy-authorization" not in last_req.headers
    assert "te" not in last_req.headers
    assert "upgrade" not in last_req.headers


@pytest.mark.asyncio
async def test_tracing_and_forwarding_headers_injected(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    last_req = mock_upstream.received_requests[-1]

    # X-Request-ID present on upstream request and client response
    req_id = last_req.headers.get("x-request-id")
    assert req_id is not None and len(req_id) > 0
    assert resp.headers.get("X-Request-ID") == req_id

    # X-Forwarded headers
    assert last_req.headers.get("x-forwarded-proto") in ("http", "https")
    assert last_req.headers.get("x-forwarded-for") is not None


@pytest.mark.asyncio
async def test_methods_and_bodies_preserved(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    project_id = "550e8400-e29b-41d4-a716-446655440000"

    # GET
    resp_get = await client.get(f"/api/v1/projects/{project_id}?view=summary")
    assert resp_get.status_code == 200
    assert mock_upstream.received_requests[-1].method == "GET"
    assert "view=summary" in str(mock_upstream.received_requests[-1].url)

    # POST
    post_payload = b'{"name": "New Project", "slug": "new-proj"}'
    resp_post = await client.post(
        "/api/v1/projects",
        content=post_payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp_post.status_code == 200
    assert mock_upstream.received_requests[-1].method == "POST"
    assert mock_upstream.received_requests[-1].read() == post_payload

    # PATCH
    patch_payload = b'{"status": "resolved"}'
    resp_patch = await client.patch(
        f"/api/v1/projects/{project_id}/issues/888",
        content=patch_payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp_patch.status_code == 200
    assert mock_upstream.received_requests[-1].method == "PATCH"
    assert mock_upstream.received_requests[-1].read() == patch_payload


@pytest.mark.asyncio
async def test_upstream_status_and_body_pass_through_unchanged(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    # Test 401 Unauthorized from upstream
    mock_upstream.response_status = 401
    mock_upstream.response_content = b'{"detail": "Missing or invalid credentials"}'
    resp_401 = await client.get("/api/v1/projects")
    assert resp_401.status_code == 401
    assert resp_401.json() == {"detail": "Missing or invalid credentials"}

    # Test 403 Forbidden from upstream
    mock_upstream.response_status = 403
    mock_upstream.response_content = b'{"detail": "Permission denied"}'
    resp_403 = await client.get("/api/v1/projects")
    assert resp_403.status_code == 403
    assert resp_403.json() == {"detail": "Permission denied"}

    # Test 500 Internal Error from upstream
    mock_upstream.response_status = 500
    mock_upstream.response_content = b'{"detail": "Database error"}'
    resp_500 = await client.get("/api/v1/projects")
    assert resp_500.status_code == 500
    assert resp_500.json() == {"detail": "Database error"}


@pytest.mark.asyncio
async def test_oversized_body_returns_413(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    # base_settings configured max_request_body_bytes = 1024 (1 KB)

    # 1. Check with Content-Length header
    oversized_data = b"x" * 2000
    resp_cl = await client.post(
        "/api/v1/projects",
        content=oversized_data,
        headers={"Content-Length": str(len(oversized_data))},
    )
    assert resp_cl.status_code == 413
    assert resp_cl.json() == {"detail": "Request body too large"}

    # 2. Check with chunked / streamed upload exceeding limit
    async def stream_generator():
        for _ in range(15):
            yield b"a" * 100

    resp_stream = await client.post(
        "/api/v1/projects",
        content=stream_generator(),
    )
    assert resp_stream.status_code == 413
    assert resp_stream.json() == {"detail": "Request body too large"}

