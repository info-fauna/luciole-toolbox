import time

import pytest

from luciole_toolbox.geo import (
    CRSType,
    convert_coordinates,
    convert_coordinates_batch,
    get_CKM2,
    get_CKM2_batch,
    get_CNHA,
    get_CNHA_batch,
    get_CRS,
    get_CRS_batch,
    is_in_switzerland_bbox,
    is_in_switzerland_bbox_batch,
)

# 100x100 grid on the Swiss plateau, inside the WGS84 detection ranges.
# 46.2..47.4 N, 6.5..8.5 E.
_TEN_THOUSAND = 10_000
_WGS84 = {"source": CRSType.WGS84}


def _plateau_wgs84(n=_TEN_THOUSAND):
    side = 100
    if side * side != n:
        raise ValueError(f"expected {side * side} points, got {n}")
    coords = []
    for row in range(side):
        lat = 46.2 + row * (1.2 / (side - 1))
        for col in range(side):
            lon = 6.5 + col * (2.0 / (side - 1))
            coords.append((lat, lon))
    return coords


def _lv03_pair_is_int(value):
    assert type(value[0]) is int
    assert type(value[1]) is int


@pytest.mark.parametrize(
    "batch, scalar, kwargs, check",
    [
        (get_CRS_batch, get_CRS, {}, None),
        pytest.param(
            get_CKM2_batch,
            get_CKM2,
            _WGS84,
            None,
            marks=pytest.mark.integration,
        ),
        pytest.param(
            get_CNHA_batch,
            get_CNHA,
            _WGS84,
            None,
            marks=pytest.mark.integration,
        ),
        pytest.param(
            is_in_switzerland_bbox_batch,
            is_in_switzerland_bbox,
            _WGS84,
            None,
            marks=pytest.mark.integration,
        ),
        pytest.param(
            convert_coordinates_batch,
            convert_coordinates,
            {"target": CRSType.LV03, "source": CRSType.WGS84},
            _lv03_pair_is_int,
            marks=pytest.mark.integration,
        ),
    ],
    ids=[
        "get_CRS",
        "get_CKM2",
        "get_CNHA",
        "is_in_switzerland_bbox",
        "convert_coordinates",
    ],
)
def test_batch_ten_thousand_points_within_half_a_second(batch, scalar, kwargs, check):
    coords = _plateau_wgs84()

    # Prime the cached transformer (and the grid-shift download) so the bound
    # measures the batch call, not a one-time network fetch.
    batch(coords[:1], **kwargs)

    start = time.perf_counter()
    result = batch(coords, **kwargs)
    elapsed = time.perf_counter() - start

    assert len(result) == _TEN_THOUSAND
    assert None not in result
    for index in (0, _TEN_THOUSAND // 2, _TEN_THOUSAND - 1):
        assert result[index] == scalar(*coords[index], **kwargs)
        if check is not None:
            check(result[index])

    assert elapsed < 0.5, f"10_000 points took {elapsed:.3f}s (max 0.5s)"
