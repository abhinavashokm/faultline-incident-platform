import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import request_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = str(uuid.uuid4())

        token = request_id_var.set(req_id)
        request.state.request_id = req_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_var.reset(token)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int | None = None):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes or settings.max_request_body_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check Content-Length header first if present
        content_length = request.headers.get("Content-Length")
        if content_length is not None:
            try:
                length = int(content_length)
                if length > self.max_body_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Request body exceeds limit of {self.max_body_bytes} bytes"},
                    )
            except ValueError:
                pass

        # For chunked or unverified content-length, verify during body consumption
        body = await request.body()
        if len(body) > self.max_body_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds limit of {self.max_body_bytes} bytes"},
            )

        return await call_next(request)

