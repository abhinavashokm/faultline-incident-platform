import time
from typing import Any, Callable, Coroutine

from faultline._internal import logger
from faultline.client import Client, get_client
from faultline.redaction import redact_headers

Scope = dict[str, Any]
Receive = Callable[[], Coroutine[Any, Any, dict[str, Any]]]
Send = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


def extract_asgi_headers(scope: Scope) -> dict[str, str]:
    """Extract and decode headers from ASGI scope into a string dictionary."""
    headers: dict[str, str] = {}
    raw_headers = scope.get("headers") or []
    for item in raw_headers:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            try:
                key = item[0].decode("latin-1").lower()
                val = item[1].decode("latin-1")
                headers[key] = val
            except Exception:
                continue
    return headers


def build_request_context(scope: Scope) -> dict[str, Any]:
    """Extract safe request context from ASGI scope."""
    headers = extract_asgi_headers(scope)
    scrubbed_headers = redact_headers(headers)

    query_string = ""
    raw_query = scope.get("query_string")
    if isinstance(raw_query, (bytes, bytearray)):
        query_string = raw_query.decode("latin-1", errors="replace")

    client_info = scope.get("client")
    client_ip = client_info[0] if (isinstance(client_info, (list, tuple)) and len(client_info) > 0) else None

    return {
        "url": scope.get("path", ""),
        "query_string": query_string,
        "headers": scrubbed_headers,
        "client_ip": client_ip,
    }


class FaultlineASGIMiddleware:
    """Pure ASGI middleware capturing unhandled exceptions and performance telemetry.

    Zero third-party dependencies (no Starlette or FastAPI imports).
    Re-raises caught exceptions after capturing.
    """

    def __init__(self, app: Any, client: Client | None = None) -> None:
        self.app = app
        self.client = client

    def get_route_template(self, scope: Scope) -> str | None:
        """Resolve route template from ASGI scope.

        Returns route path if available, or None. Never returns the raw request path.
        """
        route = scope.get("route")
        if route is not None and hasattr(route, "path"):
            return getattr(route, "path")
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        status_code: int | None = None
        method = (scope.get("method") or "GET").upper()

        async def wrapped_send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = message.get("status")
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        except Exception as exc:
            duration_s = time.perf_counter() - start_time
            # If an exception escapes the application, standard status is 500
            effective_status = status_code if status_code is not None else 500
            route_template = self.get_route_template(scope)
            context = build_request_context(scope)
            context["duration_seconds"] = round(duration_s, 6)

            active_client = self.client or get_client()
            if active_client is not None:
                try:
                    active_client.capture_exception(
                        exc,
                        route_template=route_template,
                        http_method=method,
                        status_code=effective_status,
                        context=context,
                    )
                except Exception as sdk_err:
                    logger.error("Faultline ASGI middleware failed to capture error: %s", sdk_err)

            # Record performance for error request if performance monitor exists
            self._record_performance(method, route_template, effective_status, duration_s)

            # Must re-raise the original exception
            raise
        else:
            duration_s = time.perf_counter() - start_time
            effective_status = status_code if status_code is not None else 200
            route_template = self.get_route_template(scope)
            self._record_performance(method, route_template, effective_status, duration_s)

    def _record_performance(
        self,
        method: str,
        route_template: str | None,
        status: int,
        duration: float,
    ) -> None:
        """Record request duration and metrics for batched performance telemetry."""
        try:
            from faultline.performance import record_request
            record_request(
                method=method,
                route_template=route_template,
                status_code=status,
                duration=duration,
                client=self.client or get_client(),
            )
        except Exception as exc:
            logger.debug("Failed to record performance metric: %s", exc)

