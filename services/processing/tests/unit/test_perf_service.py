import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.messaging.consumer import PermanentError
from app.perf.schemas import EventEnvelope, NormalizedPerformanceBatch, RouteMetric
from app.perf.service import PerfService, pre_aggregate_metrics


def test_pre_aggregate_metrics_combines_duplicates():
    m1 = RouteMetric(
        route="/users/{id}",
        method="GET",
        request_count=10,
        error_count=1,
        status_counts={"200": 9, "500": 1},
        histogram_version=1,
        latency_histogram=[5, 3, 1, 1, 0, 0],
    )
    m2 = RouteMetric(
        route="/users/{id}",
        method="GET",
        request_count=20,
        error_count=2,
        status_counts={"200": 18, "404": 2},
        histogram_version=1,
        latency_histogram=[10, 5, 3, 2, 0, 0],
    )
    m3 = RouteMetric(
        route="/posts",
        method="POST",
        request_count=5,
        error_count=0,
        status_counts={"201": 5},
        histogram_version=1,
        latency_histogram=[1, 2, 2, 0, 0, 0],
    )

    result = pre_aggregate_metrics([m1, m2, m3])
    assert len(result) == 2

    users_metric = next(m for m in result if m.route == "/users/{id}")
    assert users_metric.request_count == 30
    assert users_metric.error_count == 3
    assert users_metric.status_counts == {"200": 27, "500": 1, "404": 2}
    assert users_metric.latency_histogram == [15, 8, 4, 3, 0, 0]


@pytest.mark.asyncio
async def test_process_batch_idempotency_skip():
    batch_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    envelope = EventEnvelope(
        schema_version=1,
        event_id=batch_id,
        workspace_id=workspace_id,
        project_id=project_id,
        received_at=datetime.now(timezone.utc),
        payload=NormalizedPerformanceBatch(
            batch_id=batch_id,
            environment="production",
            release="1.0.0",
            interval_start=datetime(2026, 11, 12, 10, 0, 15, tzinfo=timezone.utc),
            interval_end=datetime(2026, 11, 12, 10, 0, 25, tzinfo=timezone.utc),
            metrics=[],
        ),
    )

    # Mock session factory and repository
    mock_session = AsyncMock()
    mock_session.begin = MagicMock()
    mock_session.begin.return_value.__aenter__ = AsyncMock()
    mock_session.begin.return_value.__aexit__ = AsyncMock()

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock()

    service = PerfService(mock_session_factory)

    # Patch repo.record_batch_if_new to return False (duplicate)
    with pytest.MonkeyPatch.context() as mp:
        mock_record = AsyncMock(return_value=False)
        mock_upsert = AsyncMock()
        mp.setattr("app.perf.service.PerfRepository.record_batch_if_new", mock_record)
        mp.setattr("app.perf.service.PerfRepository.upsert_metric_bucket", mock_upsert)

        res = await service.process_batch(envelope)

        assert res.is_duplicate is True
        assert res.metrics_count == 0
        mock_record.assert_awaited_once_with(
            batch_id=batch_id,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        mock_upsert.assert_not_called()


@pytest.mark.asyncio
async def test_process_batch_minute_truncation_and_upsert():
    batch_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    metric = RouteMetric(
        route="/checkout",
        method="POST",
        request_count=10,
        error_count=0,
        status_counts={"200": 10},
        histogram_version=1,
        latency_histogram=[5, 3, 2, 0, 0, 0],
    )

    envelope = EventEnvelope(
        schema_version=1,
        event_id=batch_id,
        workspace_id=workspace_id,
        project_id=project_id,
        received_at=datetime.now(timezone.utc),
        payload=NormalizedPerformanceBatch(
            batch_id=batch_id,
            environment="production",
            release="1.2.0",
            interval_start=datetime(2026, 11, 12, 10, 5, 45, tzinfo=timezone.utc),
            interval_end=datetime(2026, 11, 12, 10, 5, 55, tzinfo=timezone.utc),
            metrics=[metric],
        ),
    )

    mock_session = AsyncMock()
    mock_session.begin = MagicMock()
    mock_session.begin.return_value.__aenter__ = AsyncMock()
    mock_session.begin.return_value.__aexit__ = AsyncMock()

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock()

    service = PerfService(mock_session_factory)

    with pytest.MonkeyPatch.context() as mp:
        mock_record = AsyncMock(return_value=True)
        mock_upsert = AsyncMock()
        mp.setattr("app.perf.service.PerfRepository.record_batch_if_new", mock_record)
        mp.setattr("app.perf.service.PerfRepository.upsert_metric_bucket", mock_upsert)

        res = await service.process_batch(envelope)

        assert res.is_duplicate is False
        assert res.metrics_count == 1
        mock_record.assert_awaited_once()
        mock_upsert.assert_awaited_once()

        call_args = mock_upsert.call_args[0][0]
        # Verify 1-minute bucket truncation (second=0, microsecond=0)
        assert call_args["bucket_start"] == datetime(2026, 11, 12, 10, 5, 0, tzinfo=timezone.utc)
        assert call_args["service"] == ""
        assert call_args["route_template"] == "/checkout"
        assert call_args["http_method"] == "POST"
