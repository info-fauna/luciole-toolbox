import pytest

from luciole_toolbox.geo import CRSType, is_in_switzerland_bbox

# Strict Switzerland/Liechtenstein bbox in LV95 (see _CH_LV95_EASTING_RANGE/
# _CH_LV95_NORTHING_RANGE in geo.py). Used directly as LV95 input below so
# these cases exercise the identity path in convert_coordinates (no
# transformer, no network) and stay deterministic on the exact boundary.
_CH_LV95_EASTING_MIN, _CH_LV95_EASTING_MAX = 2_485_000, 2_834_000
_CH_LV95_NORTHING_MIN, _CH_LV95_NORTHING_MAX = 1_075_000, 1_296_000


@pytest.mark.integration
def test_is_in_switzerland_bbox_callable():
    is_in_switzerland_bbox(46.948, 7.447)


@pytest.mark.parametrize(
    "easting, northing",
    [
        (2_600_000, 1_200_000),
        (_CH_LV95_EASTING_MIN, 1_200_000),
        (2_600_000, _CH_LV95_NORTHING_MIN),
        (_CH_LV95_EASTING_MAX, 1_200_000),
        (2_600_000, _CH_LV95_NORTHING_MAX),
    ],
    ids=["comfortably-inside", "easting-min-edge",
         "northing-min-edge", "easting-max-edge", "northing-max-edge"],
)
def test_is_in_switzerland_bbox_lv95_inside(easting, northing):
    assert is_in_switzerland_bbox(
        easting, northing, source=CRSType.LV95) is True


@pytest.mark.parametrize(
    "easting, northing",
    [
        (2_450_000, 1_200_000),
        (2_870_000, 1_200_000),
        (2_600_000, 1_030_000),
        (2_600_000, 1_310_000),
    ],
    ids=["easting-below-min", "easting-above-max",
         "northing-below-min", "northing-above-max"],
)
def test_is_in_switzerland_bbox_lv95_outside(easting, northing):
    assert is_in_switzerland_bbox(
        easting, northing, source=CRSType.LV95) is False


@pytest.mark.integration
@pytest.mark.parametrize(
    "cx, cy, source",
    [
        (46.948, 7.447, None),
        ("46° 56.88' N", "7° 26.82' E", None),
        (600_000, 200_000, None),
        (600_000, 200_000, CRSType.LV03),
        (2_600_000, 1_200_000, CRSType.LV95),
    ],
    ids=["wgs84-decimal-bern", "wgs84-dms-bern",
         "lv03-autodetected-bern", "lv03-explicit-source-bern",
         "lv95-explicit-source-bern"],
)
def test_is_in_switzerland_bbox_inside_across_crs(cx, cy, source):
    assert is_in_switzerland_bbox(cx, cy, source=source) is True


@pytest.mark.integration
def test_is_in_switzerland_bbox_lv03_outside_via_autodetect():
    # LV03 northing past the strict CH bound but still within the
    # detection-tolerance margin, so it resolves to a real LV03 point
    # rather than None - see _LV_NEIGHBOUR_MARGIN_M in geo.py.
    assert is_in_switzerland_bbox(600_000, 300_000) is False


@pytest.mark.parametrize(
    "cx, cy",
    [
        (None, "8.044591"),
        ("46.385018", None),
        ("", ""),
        ("impossible", "8.044591"),
        (48.8566, 2.3522),
    ],
    ids=[
        "cx-none",
        "cy-none",
        "both-empty",
        "cx-non-numeric",
        "wgs84-decimal-outside-recognized-envelope",
    ],
)
def test_is_in_switzerland_bbox_unresolvable_returns_none(cx, cy):
    assert is_in_switzerland_bbox(cx, cy) is None
