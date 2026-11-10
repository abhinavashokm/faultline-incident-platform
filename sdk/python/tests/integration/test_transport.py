import json
import time
import pytest

from faultline.config import Config
from faultline.constants import EVENTS_ENDPOINT
from faultline.transport import Transport


def test_transport_202_success(make_mock_server):
    def handle(handler):
        handler.send_response(202)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(b'{"event_id": "test", "status": "accepted"}')

    server = make_mock_server(handle)
    config = Config.from_options(
        dsn=f"http://test_proj_key@127.0.0.1:{server.port}",
        flush_timeout=2.0,
    )
    transport = Transport(config)

    event_payload = {"event_id": "test-uuid-1", "message": "hello world"}
    enqueued = transport.send(event_payload)
    assert enqueued is True

    flushed = transport.flush(timeout=2.0)
    assert flushed is True

    transport.close()

    assert len(server.requests) == 1
    req = server.requests[0]
    assert req["path"] == EVENTS_ENDPOINT
    assert req["headers"]["X-Faultline-Key"] == "test_proj_key"
    assert json.loads(req["body"]) == event_payload


def test_transport_401_no_retry(make_mock_server):
    call_count = 0

    def handle(handler):
        nonlocal call_count
        call_count += 1
        handler.send_response(401)
        handler.end_headers()
        handler.wfile.write(b'{"detail": "Invalid or revoked project key"}')

    server = make_mock_server(handle)
    config = Config.from_options(
        dsn=f"http://bad_key@127.0.0.1:{server.port}",
        max_retries=3,
        flush_timeout=2.0,
    )
    transport = Transport(config)
    transport.send({"event_id": "1", "message": "error"})
    transport.flush(timeout=2.0)
    transport.close()

    # Must NOT retry on 401
    assert call_count == 1


def test_transport_429_retry_with_cap(make_mock_server):
    call_count = 0

    def handle(handler):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            handler.send_response(429)
            handler.send_header("Retry-After", "0.1")
            handler.end_headers()
            handler.wfile.write(b'{"detail": "Rate limit exceeded"}')
        else:
            handler.send_response(202)
            handler.end_headers()
            handler.wfile.write(b'{"status": "accepted"}')

    server = make_mock_server(handle)
    config = Config.from_options(
        dsn=f"http://test_key@127.0.0.1:{server.port}",
        max_retries=3,
        max_retry_after=1.0,
        flush_timeout=2.0,
    )
    transport = Transport(config)
    transport.send({"event_id": "1", "message": "error"})
    transport.flush(timeout=2.0)
    transport.close()

    # Initial 429, then backoff and retry -> 202
    assert call_count == 2


def test_transport_503_retries(make_mock_server):
    call_count = 0

    def handle(handler):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            handler.send_response(503)
            handler.end_headers()
        else:
            handler.send_response(202)
            handler.end_headers()

    server = make_mock_server(handle)
    config = Config.from_options(
        dsn=f"http://test_key@127.0.0.1:{server.port}",
        max_retries=3,
        flush_timeout=3.0,
    )
    transport = Transport(config)
    transport.send({"event_id": "1", "message": "transient error"})
    transport.flush(timeout=3.0)
    transport.close()

    assert call_count == 3


def test_transport_slow_server_timeout(make_mock_server):
    def handle(handler):
        time.sleep(1.0)
        handler.send_response(202)
        handler.end_headers()

    server = make_mock_server(handle)
    config = Config.from_options(
        dsn=f"http://test_key@127.0.0.1:{server.port}",
        timeout=0.2,
        max_retries=1,
        flush_timeout=1.0,
    )
    transport = Transport(config)
    start_time = time.monotonic()
    transport.send({"event_id": "1", "message": "slow error"})
    # Sending did not block the caller
    assert time.monotonic() - start_time < 0.1
    transport.flush(timeout=1.0)
    transport.close()


def test_transport_server_down():
    # Use a non-listening port
    config = Config.from_options(
        dsn="http://test_key@127.0.0.1:59999",
        timeout=0.2,
        max_retries=1,
        flush_timeout=1.0,
    )
    transport = Transport(config)
    start_time = time.monotonic()
    enqueued = transport.send({"event_id": "1", "message": "server down"})
    assert enqueued is True
    # Non-blocking
    assert time.monotonic() - start_time < 0.1
    transport.flush(timeout=0.5)
    transport.close()


def test_transport_queue_full_drops_newest_without_blocking():
    config = Config.from_options(
        dsn="http://test_key@127.0.0.1:59998",
        max_queue_size=2,
        timeout=1.0,
    )
    transport = Transport(config)
    # Fill the queue directly to its limit
    transport._queue.put(("http://test_key@127.0.0.1:59998", {"event_id": "q1"}))
    transport._queue.put(("http://test_key@127.0.0.1:59998", {"event_id": "q2"}))

    start_time = time.monotonic()
    # 3rd should be rejected immediately because queue is full
    res = transport.send({"event_id": "q3"})

    assert time.monotonic() - start_time < 0.1
    assert res is False  # Dropped newest

    transport.close(timeout=0.2)


def test_transport_flush_on_close(make_mock_server):
    def handle(handler):
        handler.send_response(202)
        handler.end_headers()

    server = make_mock_server(handle)
    config = Config.from_options(
        dsn=f"http://test_key@127.0.0.1:{server.port}",
        flush_timeout=2.0,
    )
    transport = Transport(config)
    transport.send({"event_id": "1"})
    transport.send({"event_id": "2"})
    # Close without manual flush
    transport.close(timeout=2.0)

    assert len(server.requests) == 2
