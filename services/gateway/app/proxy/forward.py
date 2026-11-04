import logging
from typing import AsyncIterator

import httpx
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from app.core.config import Settings
from app.errors import (
    payload_too_large_response,
    upstream_timeout_response,
    upstream_unavailable_response,
)
from app.routes.registry import RouteEntry

logger = logging.getLogger(__name__)

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

IDENTITY_HEADERS = {
    "x-user-id",
    "x-workspace-id",
    "x-forwarded-user",
    "x-role",
}


class BodyTooLargeError(Exception):
    """Raised when request body exceeds maximum allowed size."""
    pass


async def _stream_request_body(request: Request, max_bytes: int) -> AsyncIterator[bytes]:
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise BodyTooLargeError("Request body exceeded maximum allowed size")
        yield chunk


def _filter_request_headers(request: Request, settings: Settings) -> dict[str, str]:
    """Filter hop-by-hop and client identity headers while preserving credentials."""
    filtered: dict[str, str] = {}

    for key, value in request.headers.items():
        key_lower = key.lower()

        # 1. Strip hop-by-hop headers, Host, and proxy headers we will set explicitly
        if key_lower in HOP_BY_HOP_HEADERS or key_lower in (
            "host",
            "x-request-id",
            "x-forwarded-for",
            "x-forwarded-proto",
        ):
            continue

        # 2. Strip client-supplied identity headers (anti-spoofing)
        if key_lower in IDENTITY_HEADERS or key_lower.startswith("x-principal"):
            continue

        # Preserve all other headers untouched (including Authorization and SDK key headers)
        filtered[key] = value

    # Set forwarded and tracing headers
    req_id = getattr(request.state, "request_id", None)
    if req_id:
        filtered["X-Request-ID"] = req_id

    filtered["X-Forwarded-Proto"] = request.url.scheme

    client_ip = request.client.host if request.client else "127.0.0.1"
    if settings.trust_forwarded_for and "x-forwarded-for" in request.headers:
        filtered["X-Forwarded-For"] = f"{request.headers['x-forwarded-for']}, {client_ip}"
    else:
        filtered["X-Forwarded-For"] = client_ip

    return filtered


def _filter_response_headers(upstream_response: httpx.Response) -> dict[str, str]:
    """Filter hop-by-hop headers from upstream response."""
    filtered: dict[str, str] = {}
    for key, value in upstream_response.headers.items():
        if key.lower() not in HOP_BY_HOP_HEADERS:
            filtered[key] = value
    return filtered


async def forward_request(
    request: Request,
    route: RouteEntry,
    client: httpx.AsyncClient,
    settings: Settings,
) -> Response:
    """Forward incoming request to upstream service and stream response back."""
    # 1. Enforce max body size from Content-Length header if provided
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.max_request_body_bytes:
                return payload_too_large_response()
        except ValueError:
            pass

    # 2. Build target URL
    clean_path = request.url.path
    target_url = f"{route.upstream_base_url}{clean_path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # 3. Build upstream headers
    upstream_headers = _filter_request_headers(request, settings)

    # 4. Prepare request content
    content = None
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if content_length == "0":
            content = b""
        else:
            content = _stream_request_body(request, settings.max_request_body_bytes)

    # 5. Determine timeout
    timeout = None
    if route.read_timeout is not None:
        timeout = httpx.Timeout(
            connect=settings.connect_timeout_seconds,
            read=route.read_timeout,
            write=settings.read_timeout_seconds,
            pool=settings.connect_timeout_seconds,
        )

    # 6. Execute upstream request
    try:
        upstream_req = client.build_request(
            method=request.method,
            url=target_url,
            headers=upstream_headers,
            content=content,
            timeout=timeout,
        )
        upstream_resp = await client.send(upstream_req, stream=True)
    except BodyTooLargeError:
        return payload_too_large_response()
    except (httpx.ConnectError, httpx.NetworkError, httpx.ConnectTimeout) as exc:
        logger.error(
            "Upstream connection failure for [%s] %s: %s",
            route.service_name,
            clean_path,
            exc,
        )
        return upstream_unavailable_response()
    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
        logger.error(
            "Upstream timeout for [%s] %s: %s",
            route.service_name,
            clean_path,
            exc,
        )
        return upstream_timeout_response()
    except httpx.HTTPError as exc:
        logger.error(
            "Upstream HTTP error for [%s] %s: %s",
            route.service_name,
            clean_path,
            exc,
        )
        return upstream_unavailable_response()

    # 7. Stream upstream response back to client
    filtered_response_headers = _filter_response_headers(upstream_resp)

    async def response_streamer() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream_resp.aiter_bytes():
                yield chunk
        finally:
            await upstream_resp.aclose()

    return StreamingResponse(
        content=response_streamer(),
        status_code=upstream_resp.status_code,
        headers=filtered_response_headers,
    )
