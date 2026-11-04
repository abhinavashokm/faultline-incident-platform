from typing import AsyncIterator, Callable
import pytest
import httpx

from app.core.config import Settings
from app.main import create_app
from app.middleware.rate_limit import MemoryRateLimiter


@pytest.fixture
def base_settings() -> Settings:
    """Settings fixture configured for local/testing environments."""
    return Settings(
        upstream_control_plane_url="http://control-plane:8000",
        upstream_ingestion_url="http://ingestion:8001",
        upstream_processing_url="http://processing-api:8002",
        cors_origins=["http://localhost:3000", "http://app.example.com"],
        rate_limit_requests=5,
        rate_limit_window_seconds=60,
        rate_limit_strategy="memory",
        connect_timeout_seconds=1.0,
        read_timeout_seconds=2.0,
        ingestion_read_timeout_seconds=2.0,
        max_request_body_bytes=1024,  # 1 KB for easy testing of limits
        trust_forwarded_for=False,
    )


class MockUpstreamState:
    """Captures requests sent to mock upstreams and allows setting custom responses."""

    def __init__(self) -> None:
        self.received_requests: list[httpx.Request] = []
        self.response_status: int = 200
        self.response_headers: dict[str, str] = {"Content-Type": "application/json"}
        self.response_content: bytes = b'{"status": "upstream-ok"}'
        self.exception_to_raise: Exception | None = None
        self.custom_handler: Callable[[httpx.Request], httpx.Response] | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.received_requests.append(request)
        if self.exception_to_raise:
            raise self.exception_to_raise
        if self.custom_handler:
            return self.custom_handler(request)
        return httpx.Response(
            status_code=self.response_status,
            headers=self.response_headers,
            content=self.response_content,
        )


@pytest.fixture
def mock_upstream() -> MockUpstreamState:
    return MockUpstreamState()


@pytest.fixture
async def app_with_mock(
    base_settings: Settings,
    mock_upstream: MockUpstreamState,
) -> AsyncIterator[tuple[httpx.AsyncClient, MockUpstreamState]]:
    """Creates a gateway application with an httpx.MockTransport for upstreams."""
    app = create_app(custom_settings=base_settings)

    # Set up mock transport for outbound requests
    transport = httpx.MockTransport(mock_upstream.handler)
    mock_client = httpx.AsyncClient(transport=transport)
    app.state.http_client = mock_client
    app.state.rate_limiter = MemoryRateLimiter(
        limit=base_settings.rate_limit_requests,
        window_seconds=base_settings.rate_limit_window_seconds,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client, mock_upstream

    await mock_client.aclose()

