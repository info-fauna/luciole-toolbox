import time

import pytest

from luciole_toolbox.geo import CRSType, GeoPoint, convert_coordinates, convert_coordinates_seq

# 100x100 grid on the Swiss plateau, inside the WGS84 detection ranges.
# 46.2..47.4 N, 6.5..8.5 E.
_TEN_THOUSAND = 10_000


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


def test_convert_coordinates_seq_empty():
    assert convert_coordinates_seq([]) == []


def test_convert_coordinates_seq_default_target_is_lv03():
    result = convert_coordinates_seq([(646614.59, 137252.17)], source=CRSType.LV03)
    assert result == [(646615, 137252)]
    assert type(result[0][0]) is int
    assert type(result[0][1]) is int


def test_convert_coordinates_invalid_source_raises():
    with pytest.raises(TypeError):
        convert_coordinates_seq([(646614.59, 137252.17)], source="WGS844")


def test_convert_coordinates_seq_invalid_target_raises():
    with pytest.raises(TypeError):
        convert_coordinates_seq([(646614.59, 137252.17)], target="not-a-crs")


def test_convert_coordinates_seq_explicit_source_skips_detection(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("get_CRS should not run when source is given")

    monkeypatch.setattr("luciole_toolbox.geo.get_CRS", _fail)
    result = convert_coordinates_seq(
        [(646614.59, 137252.17), (1.0, 2.0)],
        target=CRSType.LV03,
        source=CRSType.LV03,
    )
    assert result == [(646615, 137252), None]


def test_convert_coordinates_seq_detects_each_pair_when_source_omitted(monkeypatch):
    calls = {"n": 0}
    real = GeoPoint.parse.__func__

    def _wrapped(cls, cx, cy, source=None):
        calls["n"] += 1
        return real(cls, cx, cy, source=source)

    monkeypatch.setattr(GeoPoint, "parse", classmethod(_wrapped))
    coords = [(646614.59, 137252.17), (600072.37, 200147.07), (1.0, 2.0)]
    result = convert_coordinates_seq(coords, target=CRSType.LV03)
    assert calls["n"] == len(coords)
    assert result == [(646615, 137252), (600072, 200147), None]


def test_convert_coordinates_seq_lv_swapped_columns_match():
    straight = convert_coordinates_seq(
        [(646614.59, 137252.17)],
        target=CRSType.LV03,
        source=CRSType.LV03,
    )
    swapped = convert_coordinates_seq(
        [(137252.17, 646614.59)],
        target=CRSType.LV03,
        source=CRSType.LV03,
    )
    assert straight == swapped == [(646615, 137252)]


def test_convert_coordinates_seq_keeps_position_of_unresolved_pairs():
    coords = [(646614.59, 137252.17), (1.0, 2.0), ("646'614.59", "137'252.17")]
    assert convert_coordinates_seq(coords, target=CRSType.LV03, source=CRSType.LV03) == [
        (646615, 137252),
        None,
        (646615, 137252),
    ]


@pytest.mark.parametrize(
    "coords, source",
    [
        ([(420000, 137000)], CRSType.LV03),
        ([(2646614.59, 1137252.17)], CRSType.LV03),
        ([(646614.59, 137252.17)], CRSType.WGS84),
    ],
    ids=["lv03-below-margin", "lv95-values-labelled-lv03", "lv03-values-labelled-wgs84"],
)
def test_convert_coordinates_seq_invalid_pair_is_none(coords, source):
    assert convert_coordinates_seq(coords, target=CRSType.LV95, source=source) == [None]


@pytest.mark.integration
@pytest.mark.parametrize("target", list(CRSType))
def test_convert_coordinates_seq_matches_convert_coordinates(target):
    coords = [
        (46.427166, 6.101633),
        (6.113611, 46.481388),
        (646614.59, 137252.17),
        (137252.17, 646614.59),
        (2646614.59, 1137252.17),
        (2583097.5, 1212273.0),
        (None, None),
    ]
    assert convert_coordinates_seq(coords, target=target) == [
        convert_coordinates(cx, cy, target=target) for cx, cy in coords
    ]


@pytest.mark.integration
def test_convert_coordinates_seq_explicit_source_matches_scalar():
    coords = [(46.427166, 6.101633), (8.044591, 46.385018), (1.0, 2.0)]
    assert convert_coordinates_seq(coords, target=CRSType.LV03, source=CRSType.WGS84) == [
        convert_coordinates(cx, cy, target=CRSType.LV03, source=CRSType.WGS84) for cx, cy in coords
    ]


@pytest.mark.integration
def test_convert_coordinates_seq_lv03_to_lv95_reference():
    # Same swisstopo REFRAME points as test_convert_coordinates, including an
    # input with thousand separators, converted together in one batch.
    result = convert_coordinates_seq(
        [("646'614.59", "137'252.17"), (497230.717, 142635.171)],
        target=CRSType.LV95,
        source=CRSType.LV03,
    )
    assert result[0] == (2646614, 1137252)
    assert result[1] == pytest.approx((2497230.717, 1142635.171), rel=1e-5)


@pytest.mark.integration
def test_convert_coordinates_seq_ten_thousand_points_within_half_a_second():
    coords = _plateau_wgs84()
    # Prime the cached transformer (and the grid-shift download) so the bound
    # measures the batch conversion, not a one-time network fetch.
    convert_coordinates_seq(coords[:1], target=CRSType.LV03, source=CRSType.WGS84)

    start = time.perf_counter()
    result = convert_coordinates_seq(coords, target=CRSType.LV03, source=CRSType.WGS84)
    elapsed = time.perf_counter() - start

    assert len(result) == _TEN_THOUSAND
    assert None not in result
    for index in (0, _TEN_THOUSAND // 2, _TEN_THOUSAND - 1):
        assert result[index] == convert_coordinates(
            *coords[index], target=CRSType.LV03, source=CRSType.WGS84
        )
        assert type(result[index][0]) is int
        assert type(result[index][1]) is int
    # About a few hundredths of a second locally for this WGS84 -> LV03
    # batch. One second leaves room for a slower CI runner.
    assert elapsed < 0.5, f"10_000 points took {elapsed:.3f}s (max 0.5s)"


@pytest.mark.integration
def test_convert_coordinates_seq_multiple_identical_pairs():
    coords = [
        (646614.59, 137252.17),
        (1.0, 2.0),
        ("646'614.59", "137'252.17"),
        (646614.59, 137252.17),
    ]
    assert convert_coordinates_seq(coords, target=CRSType.LV03, source=CRSType.LV03) == [
        (646615, 137252),
        None,
        (646615, 137252),
        (646615, 137252),
    ]
