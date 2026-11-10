from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
from typing import Any, Callable
import pytest

from faultline.constants import EVENTS_ENDPOINT


class MockRequestHandler(BaseHTTPRequestHandler):
    handler_func: Callable[[BaseHTTPRequestHandler], None]

    def do_POST(self):
        self.server.requests.append({
            "path": self.path,
            "headers": dict(self.headers),
            "body": self.rfile.read(int(self.headers.get("Content-Length", 0))),
        })
        self.server.handler_func(self)

    def log_message(self, format, *args):
        # Silence default stderr logging during tests
        pass


class MockIngestServer:
    def __init__(self, handler_func: Callable[[BaseHTTPRequestHandler], None]):
        self.server = HTTPServer(("127.0.0.1", 0), MockRequestHandler)
        self.server.requests = []
        self.server.handler_func = handler_func
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}{EVENTS_ENDPOINT}"

    @property
    def requests(self) -> list[dict[str, Any]]:
        return self.server.requests

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1.0)


@pytest.fixture
def make_mock_server():
    servers = []

    def _make(handler_func: Callable[[BaseHTTPRequestHandler], None]) -> MockIngestServer:
        server = MockIngestServer(handler_func)
        servers.append(server)
        return server

    yield _make

    for s in servers:
        s.shutdown()

