import asyncio
from unittest.mock import MagicMock
import pytest

from faultline.integrations.asgi import FaultlineASGIMiddleware
from faultline.integrations.fastapi import FaultlineFastAPIMiddleware


class DummyRoute:
    def __init__(self, path: str):
        self.path = path

    def matches(self, scope):
        # Full match if path template matches prefix
        if scope.get("path", "").startswith("/users/"):
            return 1, scope
        return 0, scope


class DummyFastAPIApp:
    def __init__(self):
        self.routes = [DummyRoute("/users/{user_id}")]

    async def __call__(self, scope, receive, send):
        if scope.get("path") == "/users/error":
            raise RuntimeError("FastAPI endpoint crash")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


def test_asgi_normal_request_unaffected():
    async def _run():
        received_messages = []

        async def inner_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"success"})

        client = MagicMock()
        middleware = FaultlineASGIMiddleware(inner_app, client=client)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [[b"user-agent", b"pytest"]],
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            received_messages.append(message)

        await middleware(scope, receive, send)

        assert len(received_messages) == 2
        assert received_messages[0]["status"] == 200
        assert received_messages[1]["body"] == b"success"
        # No error captured
        assert not client.capture_exception.called

    asyncio.run(_run())


def test_asgi_error_captured_and_reraised():
    async def _run():
        async def failing_app(scope, receive, send):
            raise ValueError("Application error inside ASGI")

        client = MagicMock()
        middleware = FaultlineASGIMiddleware(failing_app, client=client)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/orders/123",
            "headers": [
                [b"authorization", b"Bearer supersecrettoken"],
                [b"content-type", b"application/json"],
            ],
            "route": DummyRoute("/orders/{order_id}"),
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        # Must re-raise the original exception
        with pytest.raises(ValueError, match="Application error inside ASGI") as exc_info:
            await middleware(scope, receive, send)

        assert client.capture_exception.called
        args, kwargs = client.capture_exception.call_args
        assert args[0] is exc_info.value
        assert kwargs["http_method"] == "POST"
        # Route template used, not raw path
        assert kwargs["route_template"] == "/orders/{order_id}"
        assert kwargs["status_code"] == 500
        # Headers in context were redacted
        headers = kwargs["context"]["headers"]
        assert headers["authorization"] == "[REDACTED]"
        assert headers["content-type"] == "application/json"

    asyncio.run(_run())


def test_fastapi_route_template_normalization():
    async def _run():
        app = DummyFastAPIApp()
        client = MagicMock()
        middleware = FaultlineFastAPIMiddleware(app, client=client)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/users/error",
            "headers": [],
        }

        async def receive():
            return {"type": "http.request"}

        async def send(msg):
            pass

        with pytest.raises(RuntimeError, match="FastAPI endpoint crash"):
            await middleware(scope, receive, send)

        assert client.capture_exception.called
        _, kwargs = client.capture_exception.call_args
        # Normalized template matched from router
        assert kwargs["route_template"] == "/users/{user_id}"

    asyncio.run(_run())


def test_fastapi_unmatched_route_template_is_none():
    app = DummyFastAPIApp()
    client = MagicMock()
    middleware = FaultlineFastAPIMiddleware(app, client=client)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/unmatched/path",
        "headers": [],
    }

    # Route template must be None, never raw path
    assert middleware.get_route_template(scope) is None


def test_asgi_non_http_scope_passthrough():
    async def _run():
        passthrough = False

        async def websocket_app(scope, receive, send):
            nonlocal passthrough
            passthrough = True

        middleware = FaultlineASGIMiddleware(websocket_app)
        await middleware({"type": "websocket"}, None, None)
        assert passthrough is True

    asyncio.run(_run())
