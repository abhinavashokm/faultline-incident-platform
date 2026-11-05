from unittest.mock import MagicMock
import pytest

from faultline.client import Client, set_client
from faultline.config import Config
from faultline.performance import PerformanceBatcher


def test_performance_batcher_records_and_flushes():
    config = Config.from_options(
        dsn="https://test_key@errors.example.com",
        release="v1.0.0",
        environment="production",
        service="order-svc",
    )
    mock_client = MagicMock()
    mock_client.config = config
    mock_client.transport = MagicMock()
    mock_client.transport.send.return_value = True

    batcher = PerformanceBatcher(batch_size=5, max_buffer_size=10)

    # Record 3 requests
    batcher.record("GET", "/items/{id}", 200, 0.045, client=mock_client)
    batcher.record("POST", "/items/{id}", 201, 0.120, client=mock_client)
    batcher.record("DELETE", "/items/{id}", 500, 0.350, client=mock_client)

    # Not flushed automatically yet because batch_size is 5
    assert not mock_client.transport.send.called

    # Flush explicitly
    res = batcher.flush(client=mock_client)
    assert res is True
    assert mock_client.transport.send.called

    call_args, call_kwargs = mock_client.transport.send.call_args
    payload = call_args[0]
    assert call_kwargs["url"] == config.dsn.performance_url
    assert payload["count"] == 3
    assert payload["release"] == "v1.0.0"
    assert payload["environment"] == "production"
    assert payload["service"] == "order-svc"
    assert len(payload["records"]) == 3

    r1 = payload["records"][0]
    assert r1["method"] == "GET"
    assert r1["route_template"] == "/items/{id}"
    assert r1["status"] == 200
    assert r1["duration"] == 0.045
    assert "timestamp" in r1


def test_performance_auto_flush_on_batch_size():
    config = Config.from_options(
        dsn="https://test_key@errors.example.com",
    )
    mock_client = MagicMock()
    mock_client.config = config
    mock_client.transport = MagicMock()
    mock_client.transport.send.return_value = True

    batcher = PerformanceBatcher(batch_size=2, max_buffer_size=10)
    batcher.record("GET", "/a", 200, 0.01, client=mock_client)
    assert not mock_client.transport.send.called

    # 2nd record triggers auto-flush
    batcher.record("GET", "/b", 200, 0.02, client=mock_client)
    assert mock_client.transport.send.called


def test_performance_buffer_capacity_bounded():
    config = Config.from_options(
        dsn="https://test_key@errors.example.com",
    )
    mock_client = MagicMock()
    mock_client.config = config
    mock_client.transport = MagicMock()
    mock_client.transport.send.return_value = True

    # Small capacity buffer with large batch size so it doesn't auto-flush
    batcher = PerformanceBatcher(batch_size=10, max_buffer_size=2)
    batcher.record("GET", "/1", 200, 0.01, client=mock_client)
    batcher.record("GET", "/2", 200, 0.01, client=mock_client)
    # 3rd should be dropped without crashing
    batcher.record("GET", "/3", 200, 0.01, client=mock_client)

    assert len(batcher._buffer) == 2
