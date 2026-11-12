import math

from faultline.constants import CURRENT_HISTOGRAM_VERSION, HISTOGRAM_V1


def test_histogram_v1_contract():
    """Assert HISTOGRAM_V1 exactly matches the canonical histogram-versioning.md specification.
    
    Upper bounds in ms: [50, 100, 250, 500, 1000, inf]
    """
    assert list(HISTOGRAM_V1) == [50, 100, 250, 500, 1000, float("inf")]
    assert len(HISTOGRAM_V1) == 6
    assert math.isinf(HISTOGRAM_V1[-1])
    assert CURRENT_HISTOGRAM_VERSION == 1
