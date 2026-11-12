import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.messaging.consumer import PermanentError
from app.perf.repository import PerfRepository


@pytest.mark.asyncio
async def test_upsert_metric_bucket_version_mismatch_raises_permanent_error():
    mock_session = AsyncMock()

    # When rowcount is 0 (due to WHERE histogram_version = EXCLUDED.histogram_version mismatch)
    mock_execute_result = MagicMock()
    mock_execute_result.rowcount = 0

    # Query for existing version returns version 1
    mock_existing_result = MagicMock()
    mock_existing_result.scalar_one_or_none.return_value = 1

    mock_session.execute.side_effect = [mock_execute_result, mock_existing_result]

    repo = PerfRepository(mock_session)

    item = {
        "workspace_id": uuid.uuid4(),
        "project_id": uuid.uuid4(),
        "environment": "production",
        "service": "",
        "route_template": "/checkout",
        "http_method": "POST",
        "release": "1.0.0",
        "bucket_start": datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc),
        "request_count": 10,
        "error_count": 0,
        "status_counts": json.dumps({"200": 10}),
        "latency_histogram": [10, 0, 0, 0, 0, 0],
        "histogram_version": 2,  # Incoming is version 2, while existing row is version 1
    }

    with pytest.raises(PermanentError, match="Histogram version mismatch"):
        await repo.upsert_metric_bucket(item)
