from typing import Mapping
from fastapi.responses import JSONResponse

from app.core.logging import request_id_var


def make_json_error(
    status_code: int,
    detail: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Construct a standardized JSON error response with X-Request-ID header."""
    response_headers = dict(headers or {})
    req_id = request_id_var.get("-")
    if req_id != "-":
        response_headers["X-Request-ID"] = req_id

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=response_headers,
    )


def not_found_response() -> JSONResponse:
    return make_json_error(status_code=404, detail="Not found")


def upstream_unavailable_response() -> JSONResponse:
    return make_json_error(status_code=502, detail="Upstream unavailable")


def upstream_timeout_response() -> JSONResponse:
    return make_json_error(status_code=504, detail="Upstream timeout")


def rate_limit_exceeded_response(retry_after: int = 60) -> JSONResponse:
    return make_json_error(
        status_code=429,
        detail="Too many requests",
        headers={"Retry-After": str(retry_after)},
    )


def payload_too_large_response() -> JSONResponse:
    return make_json_error(status_code=413, detail="Request body too large")

