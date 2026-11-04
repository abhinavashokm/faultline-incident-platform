import re
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

# Sane request ID: alphanumeric, hyphen, underscore, dot; 1-64 chars
SANE_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")


def is_sane_request_id(req_id: str | None) -> bool:
    if not req_id:
        return False
    return bool(SANE_REQUEST_ID_REGEX.match(req_id.strip()))


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensures every request has a validated or generated X-Request-ID."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming_id = request.headers.get("x-request-id")
        if incoming_id and is_sane_request_id(incoming_id):
            req_id = incoming_id.strip()
        else:
            req_id = str(uuid.uuid4())

        token = request_id_var.set(req_id)
        request.state.request_id = req_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_var.reset(token)

