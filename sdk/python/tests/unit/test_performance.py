import time
from unittest.mock import MagicMock
import pytest

from faultline.client import Client
from faultline.config import Config
from faultline.constants import CURRENT_HISTOGRAM_VERSION, HISTOGRAM_V1
from faultline.performance import PerformanceBatcher, get_histogram_bucket_index


def test_histogram_bucket_index_boundaries():
    # HISTOGRAM_V1 = [50, 100, 250, 500, 1000, inf]
    # Boundaries: <= 50 -> 0
    assert get_histogram_bucket_index(0.0) == 0
    assert get_histogram_bucket_index(50.0) == 0

    # 51 -> bucket 1 (50, 100]
    assert get_histogram_bucket_index(50.0001) == 1
    assert get_histogram_bucket_index(51.0) == 1
    assert get_histogram_bucket_index(100.0) == 1

    # (100, 250] -> bucket 2
    assert get_histogram_bucket_index(100.001) == 2
    assert get_histogram_bucket_index(250.0) == 2

    # (250, 500] -> bucket 3
    assert get_histogram_bucket_index(250.001) == 3
    assert get_histogram_bucket_index(500.0) == 3

    # (500, 1000] -> bucket 4
    assert get_histogram_bucket_index(500.001) == 4
    assert get_histogram_bucket_index(1000.0) == 4

    # > 1000 -> bucket 5 (inf)
    assert get_histogram_bucket_index(1000.001) == 5
    assert get_histogram_bucket_index(1001.0) == 5
    assert get_histogram_bucket_index(99999.0) == 5


def test_performance_batcher_records_and_aggregates():
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

    # Disable timer flush by setting flush_interval=0 for this test
    batcher = PerformanceBatcher(batch_size=10, max_buffer_size=10, flush_interval=0)

    try:
        # Record requests for the same route and method
        # 0.045s = 45ms -> bucket 0 (<= 50)
        batcher.record("GET", "/items/{id}", 200, 0.045, client=mock_client)
        # 0.051s = 51ms -> bucket 1 (50, 100]
        batcher.record("GET", "/items/{id}", 200, 0.051, client=mock_client)
        # 0.120s = 120ms -> bucket 2 (100, 250]
        batcher.record("GET", "/items/{id}", 404, 0.120, client=mock_client)
        # 1.001s = 1001ms -> bucket 5 (> 1000)
        batcher.record("GET", "/items/{id}", 500, 1.001, client=mock_client)

        # Record a request for a different method
        batcher.record("POST", "/items/{id}", 201, 0.350, client=mock_client)

        # Not flushed yet
        assert not mock_client.transport.send.called

        # Explicit flush
        res = batcher.flush(client=mock_client)
        assert res is True
        assert mock_client.transport.send.called

        call_args, call_kwargs = mock_client.transport.send.call_args
        payload = call_args[0]
        assert call_kwargs["url"] == config.dsn.performance_url
        assert payload["release"] == "v1.0.0"
        assert payload["environment"] == "production"
        assert payload["service"] == "order-svc"
        assert "batch_id" in payload
        assert "interval_start" in payload
        assert "interval_end" in payload
        assert "metrics" in payload
        assert "records" not in payload

        metrics = payload["metrics"]
        assert len(metrics) == 2

        get_metric = next(m for m in metrics if m["method"] == "GET")
        assert get_metric["route"] == "/items/{id}"
        assert get_metric["request_count"] == 4
        # 4xx is not counted in error_count, only 5xx is (so 1 error for the 500 status)
        assert get_metric["error_count"] == 1
        assert get_metric["status_counts"] == {"200": 2, "404": 1, "500": 1}
        assert get_metric["histogram_version"] == CURRENT_HISTOGRAM_VERSION
        assert get_metric["latency_histogram"] == [1, 1, 1, 0, 0, 1]

        post_metric = next(m for m in metrics if m["method"] == "POST")
        assert post_metric["route"] == "/items/{id}"
        assert post_metric["request_count"] == 1
        assert post_metric["error_count"] == 0
        assert post_metric["status_counts"] == {"201": 1}
        assert post_metric["histogram_version"] == CURRENT_HISTOGRAM_VERSION
        # 350ms -> bucket 3 (250, 500]
        assert post_metric["latency_histogram"] == [0, 0, 0, 1, 0, 0]
    finally:
        batcher.close(client=mock_client)


def test_performance_auto_flush_on_batch_size():
    config = Config.from_options(
        dsn="https://test_key@errors.example.com",
    )
    mock_client = MagicMock()
    mock_client.config = config
    mock_client.transport = MagicMock()
    mock_client.transport.send.return_value = True

    batcher = PerformanceBatcher(batch_size=2, max_buffer_size=10, flush_interval=0)
    try:
        batcher.record("GET", "/a", 200, 0.01, client=mock_client)
        assert not mock_client.transport.send.called

        # 2nd record reaches batch_size 2, triggers auto-flush
        batcher.record("GET", "/b", 200, 0.02, client=mock_client)
        assert mock_client.transport.send.called
    finally:
        batcher.close(client=mock_client)


def test_performance_time_based_flush():
    config = Config.from_options(
        dsn="https://test_key@errors.example.com",
    )
    mock_client = MagicMock()
    mock_client.config = config
    mock_client.transport = MagicMock()
    mock_client.transport.send.return_value = True

    # Fast flush interval for testing
    batcher = PerformanceBatcher(batch_size=100, max_buffer_size=10, flush_interval=0.1)
    try:
        batcher.record("GET", "/timed", 200, 0.01, client=mock_client)
        assert not mock_client.transport.send.called

        # Wait for background timer to trigger
        time.sleep(0.25)
        assert mock_client.transport.send.called

        call_args, _ = mock_client.transport.send.call_args
        payload = call_args[0]
        assert len(payload["metrics"]) == 1
        assert payload["metrics"][0]["route"] == "/timed"
    finally:
        batcher.close(client=mock_client)


def test_performance_buffer_capacity_bounded():
    config = Config.from_options(
        dsn="https://test_key@errors.example.com",
    )
    mock_client = MagicMock()
    mock_client.config = config
    mock_client.transport = MagicMock()
    mock_client.transport.send.return_value = True

    # Buffer can hold 2 distinct keys
    batcher = PerformanceBatcher(batch_size=100, max_buffer_size=2, flush_interval=0)
    try:
        batcher.record("GET", "/route-1", 200, 0.01, client=mock_client)
        batcher.record("GET", "/route-2", 200, 0.01, client=mock_client)
        # 3rd distinct route should be dropped
        batcher.record("GET", "/route-3", 200, 0.01, client=mock_client)

        assert len(batcher._buffer) == 2

        # But existing routes can still accumulate
        batcher.record("GET", "/route-1", 200, 0.02, client=mock_client)
        assert len(batcher._buffer) == 2
        assert batcher._buffer[("GET", "/route-1", config.release, config.environment, config.service)]["request_count"] == 2
    finally:
        batcher.close(client=mock_client)
