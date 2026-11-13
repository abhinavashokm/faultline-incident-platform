import pytest
from app.core.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.database_schema == "alerting"
    assert settings.issue_events_topic == "issue-events"
    assert settings.regression_events_topic == "regression-events"
    assert settings.alerts_consumer_group == "alerting-alerts"
    assert settings.role in ("alerts", "delivery")
