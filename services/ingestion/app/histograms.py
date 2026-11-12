"""Latency histogram bucket boundaries for performance metrics.

Versions are immutable and must match the processing service.
Never edit an existing version; add a new version number for new boundaries.
"""

HISTOGRAM_BUCKETS: dict[int, list[float]] = {
    1: [50, 100, 250, 500, 1000, float("inf")],  # upper bounds in ms
}
