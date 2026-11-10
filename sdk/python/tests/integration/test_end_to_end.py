import asyncio
import json
import uuid
import pytest

import faultline
from faultline.constants import EVENTS_ENDPOINT
from faultline.integrations.fastapi import FaultlineFastAPIMiddleware


def test_fastapi_end_to_end_error_ingestion(make_mock_server):
    """End-to-end test: FastAPI raises an error, SDK captures & sends it to Mock Ingest Server,

    and the payload conforms to the Ingestion service requirements.
    """
    server = make_mock_server(
        lambda handler: (
            handler.send_response(202),
            handler.send_header("Content-Type", "application/json"),
            handler.end_headers(),
            handler.wfile.write(b'{"status": "accepted"}'),
        )
    )

    # 1. Initialize Faultline SDK
    faultline.init(
        dsn=f"http://proj_api_key_secret@127.0.0.1:{server.port}",
        release="v1.8.0",
        environment="production",
        service="checkout-service",
        install_sys_excepthook=False,
    )

    # 2. Setup application (pure ASGI or FastAPI)
    try:
        from fastapi import FastAPI
        fastapi_app = FastAPI()

        @fastapi_app.get("/items/{item_id}")
        async def get_item(item_id: int):
            raise ZeroDivisionError(f"Calculation failed for item {item_id}")

        app = FaultlineFastAPIMiddleware(fastapi_app)
    except ImportError:
        # Fallback to simulated FastAPI router if FastAPI not installed in environment
        class SimulatedRoute:
            path = "/items/{item_id}"
            def matches(self, scope):
                return 1, scope

        class SimulatedFastAPI:
            routes = [SimulatedRoute()]
            async def __call__(self, scope, receive, send):
                raise ZeroDivisionError("Calculation failed for item 42")

        app = FaultlineFastAPIMiddleware(SimulatedFastAPI())

    # 3. Simulate incoming HTTP request to /items/42
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/items/42",
        "raw_path": b"/items/42",
        "query_string": b"",
        "headers": [
            (b"authorization", b"Bearer super-secret-jwt-token"),
            (b"cookie", b"session_id=abcdef123"),
            (b"user-agent", b"EndToEndTestRunner"),
        ],
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(msg):
        pass

    # 4. Invoke request; must re-raise the exception to host
    with pytest.raises(ZeroDivisionError, match="Calculation failed for item 42"):
        asyncio.run(app(scope, receive, send))

    # 5. Flush SDK
    faultline.flush(timeout=2.0)
    faultline.close(timeout=2.0)

    # 6. Verify Ingestion received the POST /api/v1/events request
    assert len(server.requests) >= 1
    req = server.requests[0]

    assert req["path"] == EVENTS_ENDPOINT
    assert req["headers"]["X-Faultline-Key"] == "proj_api_key_secret"
    assert req["headers"]["Content-Type"] == "application/json"

    payload = json.loads(req["body"])

    # Validate against schema fields
    uuid.UUID(payload["event_id"])
    assert payload["event_type"] == "error"
    assert payload["level"] == "error"
    assert payload["exception_type"] == "ZeroDivisionError"
    assert "Calculation failed for item 42" in payload["message"]
    assert payload["release"] == "v1.8.0"
    assert payload["environment"] == "production"
    assert payload["service"] == "checkout-service"
    assert payload["http_method"] == "GET"
    assert payload["route_template"] == "/items/{item_id}"
    assert payload["status_code"] == 500
    assert "project_id" not in payload  # Hard rule: project_id NOT sent by SDK

    # Verify stacktrace frames
    frames = payload["stack_frames"]
    assert isinstance(frames, list)
    assert len(frames) > 0
    for frame in frames:
        assert "file" in frame
        assert "function" in frame
        assert "in_app" in frame

    # Verify sensitive data redaction
    ctx_headers = payload["context"]["headers"]
    assert ctx_headers["authorization"] == "[REDACTED]"
    assert ctx_headers["cookie"] == "[REDACTED]"
    assert ctx_headers["user-agent"] == "EndToEndTestRunner"

    # Verify against actual Ingestion Service Pydantic schema if available
    try:
        from app.schemas.event import ErrorEventIngestRequest
        validated = ErrorEventIngestRequest.model_validate_json(req["body"])
        assert str(validated.event_id) == payload["event_id"]
        assert validated.exception_type == "ZeroDivisionError"
        assert validated.route_template == "/items/{item_id}"
        assert validated.level == "error"
    except ImportError:
        pass
