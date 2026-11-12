"""Latency histogram bucket boundaries for performance metrics.

Versions are immutable and must match the SDK and ingestion service.
Never edit an existing version; add a new version number for new boundaries.
"""

HISTOGRAM_BUCKETS: dict[int, list[float]] = {
    1: [50.0, 100.0, 250.0, 500.0, 1000.0, float("inf")],  # upper bounds in ms
}
