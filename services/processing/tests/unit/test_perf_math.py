import math
import pytest

from app.perf.histograms import HISTOGRAM_BUCKETS
from app.perf.math import calculate_error_rate, compute_percentile, sum_histograms

V1_BOUNDARIES = HISTOGRAM_BUCKETS[1]  # [50.0, 100.0, 250.0, 500.0, 1000.0, inf]


def test_v1_contract():
    assert 1 in HISTOGRAM_BUCKETS
    assert HISTOGRAM_BUCKETS[1] == [50.0, 100.0, 250.0, 500.0, 1000.0, float("inf")]


def test_calculate_error_rate():
    assert calculate_error_rate(0, 0) == 0.0
    assert calculate_error_rate(5, 0) == 0.0
    assert calculate_error_rate(0, 100) == 0.0
    assert calculate_error_rate(1, 100) == 1.0
    assert calculate_error_rate(48, 1000) == 4.8
    assert calculate_error_rate(21, 10000) == 0.21
    assert calculate_error_rate(1, 3) == 33.33


def test_sum_histograms():
    assert sum_histograms([]) == []
    h1 = [10, 20, 30, 40, 50, 60]
    h2 = [1, 2, 3, 4, 5, 6]
    assert sum_histograms([h1, h2]) == [11, 22, 33, 44, 55, 66]


def test_compute_percentile_empty():
    assert compute_percentile([], 0.5, V1_BOUNDARIES) is None
    assert compute_percentile([0, 0, 0, 0, 0, 0], 0.5, V1_BOUNDARIES) is None
    assert compute_percentile([10, 20], 0.5, V1_BOUNDARIES) is None


def test_compute_percentile_single_bucket():
    # 100 items all in [0, 50]
    hist = [100, 0, 0, 0, 0, 0]
    # k = ceil(0.5 * 100) = 50. ratio = 50/100 = 0.5. val = 0 + 0.5 * 50 = 25
    assert compute_percentile(hist, 0.5, V1_BOUNDARIES) == 25
    # k = ceil(0.95 * 100) = 95. ratio = 95/100 = 0.95. val = 47.5 -> 48
    assert compute_percentile(hist, 0.95, V1_BOUNDARIES) == 48


def test_compute_percentile_interpolation():
    # 100 items in [0, 50], 100 items in (50, 100]
    hist = [100, 100, 0, 0, 0, 0]
    # total = 200. k for p50 = ceil(0.5 * 200) = 100. Lands in bucket 0 (count=100, k=100).
    # val = 0 + (100/100) * 50 = 50.
    assert compute_percentile(hist, 0.5, V1_BOUNDARIES) == 50
    # k for p75 = ceil(0.75 * 200) = 150.
    # bucket 1 (bounds 50 to 100), count_before=100, bucket_count=100.
    # ratio = (150 - 100)/100 = 0.5. val = 50 + 0.5 * (100 - 50) = 75.
    assert compute_percentile(hist, 0.75, V1_BOUNDARIES) == 75


def test_compute_percentile_overflow_bucket():
    # All items in overflow bucket (last bucket > 1000)
    hist = [0, 0, 0, 0, 0, 50]
    # Any percentile landing in the overflow bucket returns the last finite boundary (1000)
    assert compute_percentile(hist, 0.5, V1_BOUNDARIES) == 1000
    assert compute_percentile(hist, 0.99, V1_BOUNDARIES) == 1000

    # 90 items in [0, 50], 10 items in overflow
    hist2 = [90, 0, 0, 0, 0, 10]
    # total = 100. p95 -> k = 95 -> lands in overflow bucket -> returns 1000
    assert compute_percentile(hist2, 0.95, V1_BOUNDARIES) == 1000
    # p50 -> k = 50 -> lands in bucket 0 -> val = 0 + 50/90 * 50 = 27.77 -> 28
    assert compute_percentile(hist2, 0.50, V1_BOUNDARIES) == 28
