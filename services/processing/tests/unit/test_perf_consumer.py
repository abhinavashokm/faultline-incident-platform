import json
import uuid
from datetime import datetime, timezone

import pytest

from app.messaging.consumer import PermanentError
from app.perf.consumer import build_perf_handler, parse_and_validate_performance_message


def make_valid_perf_message(
    batch_id: str | None = None,
    histogram_version: int = 1,
    latency_histogram: list[int] | None = None,
) -> bytes:
    bid = batch_id or str(uuid.uuid4())
    histogram = latency_histogram if latency_histogram is not None else [10, 20, 5, 2, 1, 0]
    payload = {
        "schema_version": 1,
        "event_id": bid,
        "workspace_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "batch_id": bid,
            "environment": "production",
            "release": "1.0.0",
            "interval_start": "2026-11-12T10:00:00Z",
            "interval_end": "2026-11-12T10:00:10Z",
            "metrics": [
                {
                    "route": "/api/v1/checkout",
                    "method": "POST",
                    "request_count": 38,
                    "error_count": 1,
                    "status_counts": {"200": 37, "500": 1},
                    "histogram_version": histogram_version,
                    "latency_histogram": histogram,
                }
            ],
        },
    }
    return json.dumps(payload).encode("utf-8")


def test_parse_valid_perf_message():
    raw = make_valid_perf_message()
    envelope = parse_and_validate_performance_message(raw)
    assert envelope.schema_version == 1
    assert str(envelope.event_id) == str(envelope.payload.batch_id)
    assert len(envelope.payload.metrics) == 1
    assert envelope.payload.metrics[0].route == "/api/v1/checkout"
    assert envelope.payload.metrics[0].method == "POST"


def test_parse_invalid_json():
    with pytest.raises(PermanentError, match="Invalid JSON"):
        parse_and_validate_performance_message(b"not json")


def test_parse_missing_schema_version():
    data = {"event_id": str(uuid.uuid4()), "payload": {}}
    with pytest.raises(PermanentError, match="missing 'schema_version'"):
        parse_and_validate_performance_message(json.dumps(data).encode("utf-8"))


def test_parse_unsupported_schema_version():
    data = {
        "schema_version": 2,
        "event_id": str(uuid.uuid4()),
        "workspace_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": {},
    }
    with pytest.raises(PermanentError, match="Unsupported schema_version: 2"):
        parse_and_validate_performance_message(json.dumps(data).encode("utf-8"))


def test_parse_mismatched_batch_id():
    raw = make_valid_perf_message()
    data = json.loads(raw)
    data["event_id"] = str(uuid.uuid4())
    with pytest.raises(PermanentError, match="does not match payload batch_id"):
        parse_and_validate_performance_message(json.dumps(data).encode("utf-8"))


def test_parse_unknown_histogram_version():
    raw = make_valid_perf_message(histogram_version=99)
    with pytest.raises(PermanentError, match="Unknown histogram_version"):
        parse_and_validate_performance_message(raw)


def test_parse_histogram_length_mismatch():
    raw = make_valid_perf_message(latency_histogram=[1, 2, 3])  # Needs 6 elements
    with pytest.raises(PermanentError, match="does not match expected length"):
        parse_and_validate_performance_message(raw)
