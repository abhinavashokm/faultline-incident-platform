"""Pure mathematical and statistical calculations for performance metrics.

Contains percentile calculations, error rates, and histogram aggregation.
Pure functions only: no database or FastAPI dependencies.
"""

import math
from datetime import datetime, timedelta
from typing import Sequence


def determine_interval_seconds(from_time: datetime, to_time: datetime) -> int:
    """Determine timeseries interval bucket width based on the time range duration:

    - <= 2 hours: 60 seconds (1 minute)
    - <= 12 hours: 300 seconds (5 minutes)
    - <= 2 days (48 hours): 900 seconds (15 minutes)
    - > 2 days: 3600 seconds (1 hour)
    """
    duration = to_time - from_time
    if duration <= timedelta(hours=2):
        return 60
    elif duration <= timedelta(hours=12):
        return 300
    elif duration <= timedelta(days=2):
        return 900
    else:
        return 3600



def sum_histograms(histograms: Sequence[Sequence[int]]) -> list[int]:
    """Element-wise sum of histogram counts across multiple buckets."""
    if not histograms:
        return []
    length = len(histograms[0])
    total = [0] * length
    for hist in histograms:
        for i in range(min(length, len(hist))):
            total[i] += hist[i]
    return total


def calculate_error_rate(error_count: int, request_count: int) -> float:
    """Calculate error rate as a percentage rounded to 2 decimal places.

    Returns 0.0 if request_count is 0.
    Example: 48 errors out of 1000 requests -> 4.8
    """
    if request_count <= 0:
        return 0.0
    rate = (error_count / request_count) * 100.0
    return round(rate, 2)


def compute_percentile(
    histogram: Sequence[int],
    q: float,
    boundaries: Sequence[float],
) -> int | None:
    """Compute percentile from a summed latency histogram.

    Algorithm:
    1. If total requests is 0, return None.
    2. Rank k = ceil(q * total).
    3. Find the bucket containing rank k.
    4. If it's the overflow bucket (boundary is inf), return the last finite boundary (1000 ms).
    5. Otherwise, linearly interpolate between lower bound and upper bound:
       lower = 0.0 for bucket 0, else boundaries[i-1]
       upper = boundaries[i]
       val = lower + ((k - count_before) / bucket_count) * (upper - lower)
       return round(val)

    Args:
        histogram: Array of bucket counts.
        q: Percentile rank between 0.0 and 1.0 (e.g. 0.50, 0.95, 0.99).
        boundaries: Upper bounds for each bucket (e.g. [50.0, 100.0, 250.0, 500.0, 1000.0, inf]).

    Returns:
        Percentile latency in milliseconds as int, or None if empty.
    """
    if not histogram or len(histogram) != len(boundaries):
        return None

    total = sum(histogram)
    if total <= 0:
        return None

    # rank k between 1 and total
    k = math.ceil(q * total)
    if k <= 0:
        k = 1

    accum = 0
    for i, count in enumerate(histogram):
        if count <= 0:
            continue
        accum += count
        if accum >= k:
            upper = boundaries[i]
            # Overflow bucket check
            if math.isinf(upper):
                # Return the last finite boundary
                for b in reversed(boundaries):
                    if not math.isinf(b):
                        return int(b)
                return 1000

            lower = 0.0 if i == 0 else boundaries[i - 1]
            count_before = accum - count
            ratio = (k - count_before) / count
            val = lower + ratio * (upper - lower)
            return round(val)

    # Fallback to last finite boundary if roundoff occurred
    for b in reversed(boundaries):
        if not math.isinf(b):
            return int(b)
    return 1000
