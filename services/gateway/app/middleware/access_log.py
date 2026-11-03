import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

logger = logging.getLogger("gateway.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Logs one structured line per request containing method, path, status,
    upstream, latency in ms, and request_id.

    Never logs headers, query params (which may contain tokens), or request bodies.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            upstream_name = getattr(request.state, "upstream_name", "-")
            req_id = getattr(request.state, "request_id", request_id_var.get("-"))

            # Log sanitized request path only (no query strings, no headers, no body)
            logger.info(
                "%s %s %d upstream=%s latency_ms=%.2f request_id=%s",
                request.method,
                request.url.path,
                status_code,
                upstream_name,
                latency_ms,
                req_id,
            )

