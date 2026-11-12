"""Constants used across the Faultline SDK."""

EVENTS_ENDPOINT = "/api/v1/events"
PERFORMANCE_ENDPOINT = "/api/v1/ingest/performance"

# Histogram versioning (immutable upper bounds in milliseconds)
HISTOGRAM_V1 = [50, 100, 250, 500, 1000, float("inf")]
CURRENT_HISTOGRAM_VERSION = 1

