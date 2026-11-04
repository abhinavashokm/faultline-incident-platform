import uuid
import pytest
import httpx
from tests.conftest import MockUpstreamState


@pytest.mark.asyncio
async def test_request_id_generated_when_absent(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200

    generated_id = resp.headers.get("X-Request-ID")
    assert generated_id is not None
    # Validate UUID4 format
    parsed_uuid = uuid.UUID(generated_id)
    assert parsed_uuid.version == 4

    # Verify upstream received the exact same generated ID
    upstream_req = mock_upstream.received_requests[-1]
    assert upstream_req.headers.get("x-request-id") == generated_id


@pytest.mark.asyncio
async def test_request_id_reused_when_valid(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    valid_id = "req-123456_abcdef.test"

    resp = await client.get("/api/v1/projects", headers={"X-Request-ID": valid_id})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == valid_id

    upstream_req = mock_upstream.received_requests[-1]
    assert upstream_req.headers.get("x-request-id") == valid_id


@pytest.mark.asyncio
async def test_request_id_replaced_when_invalid(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock

    # 1. Invalid characters (spaces, special chars)
    invalid_chars_id = "bad id with spaces; select * from"
    resp = await client.get("/api/v1/projects", headers={"X-Request-ID": invalid_chars_id})
    assert resp.status_code == 200
    req_id_1 = resp.headers.get("X-Request-ID")
    assert req_id_1 != invalid_chars_id
    # Valid UUID generated
    assert uuid.UUID(req_id_1).version == 4

    # 2. Too long (> 64 chars)
    too_long_id = "a" * 100
    resp_2 = await client.get("/api/v1/projects", headers={"X-Request-ID": too_long_id})
    assert resp_2.status_code == 200
    req_id_2 = resp_2.headers.get("X-Request-ID")
    assert req_id_2 != too_long_id
    assert uuid.UUID(req_id_2).version == 4


@pytest.mark.asyncio
async def test_request_id_present_on_error_responses(
    app_with_mock: tuple[httpx.AsyncClient, MockUpstreamState],
):
    client, mock_upstream = app_with_mock
    client_id = "trace-err-999"

    # 404 response
    resp_404 = await client.get("/api/v1/unknown", headers={"X-Request-ID": client_id})
    assert resp_404.status_code == 404
    assert resp_404.headers.get("X-Request-ID") == client_id

