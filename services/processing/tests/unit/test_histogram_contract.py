from app.perf.histograms import HISTOGRAM_BUCKETS


def test_v1_histogram_boundary_contract():
    """Assert that histogram version 1 boundaries strictly match the architecture contract:

    v1 (upper bounds in ms): [50, 100, 250, 500, 1000, inf]
    """
    assert 1 in HISTOGRAM_BUCKETS
    v1_buckets = HISTOGRAM_BUCKETS[1]
    expected = [50.0, 100.0, 250.0, 500.0, 1000.0, float("inf")]
    assert v1_buckets == expected
    assert len(v1_buckets) == 6
