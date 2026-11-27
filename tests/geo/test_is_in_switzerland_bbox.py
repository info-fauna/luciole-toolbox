import pytest

from luciole_toolbox.geo import CRSType, is_in_switzerland_bbox, is_in_switzerland_bbox_batch

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
    ids=[
        "comfortably-inside",
        "easting-min-edge",
        "northing-min-edge",
        "easting-max-edge",
        "northing-max-edge",
    ],
)
def test_is_in_switzerland_bbox_lv95_inside(easting, northing):
    assert is_in_switzerland_bbox(easting, northing, source=CRSType.LV95) is True


@pytest.mark.parametrize(
    "easting, northing",
    [
        (2_450_000, 1_200_000),
        (2_870_000, 1_200_000),
        (2_600_000, 1_030_000),
        (2_600_000, 1_310_000),
    ],
    ids=["easting-below-min", "easting-above-max", "northing-below-min", "northing-above-max"],
)
def test_is_in_switzerland_bbox_lv95_outside(easting, northing):
    assert is_in_switzerland_bbox(easting, northing, source=CRSType.LV95) is False


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
    ids=[
        "wgs84-decimal-bern",
        "wgs84-dms-bern",
        "lv03-autodetected-bern",
        "lv03-explicit-source-bern",
        "lv95-explicit-source-bern",
    ],
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


@pytest.mark.parametrize(
    "cx, cy, allowed_buffer_km, expected",
    [
        # 46.108565, 5.823456: Bellegarde-sur-Valserine (~10km from the border)
        (46.108565, 5.823456, 0, False),
        (46.108565, 5.823456, 5, False),
        (46.108565, 5.823456, 10, True),
    ],
)
def test_is_in_switzerland_bbox_allowed_buffer_km(cx, cy, allowed_buffer_km, expected):
    assert is_in_switzerland_bbox(cx, cy, allowed_buffer_km=allowed_buffer_km) is expected


# LV95 only: identity path, no transformer and no network.
_BATCH_COORDS = [
    (2_600_000, 1_200_000),
    (_CH_LV95_EASTING_MIN, 1_200_000),
    (2_600_000, _CH_LV95_NORTHING_MIN),
    (_CH_LV95_EASTING_MAX, _CH_LV95_NORTHING_MAX),
    (2_450_000, 1_200_000),
    (2_600_000, 1_310_000),
    (None, None),
    ("", ""),
    (2_600_000, 1_200_000),
]


def test_is_in_switzerland_bbox_batch_empty():
    assert is_in_switzerland_bbox_batch([]) == []


def test_is_in_switzerland_bbox_batch_string_raises():
    with pytest.raises(TypeError):
        is_in_switzerland_bbox_batch("2600000, 1200000")


@pytest.mark.parametrize("source", [None, CRSType.LV95], ids=["autodetect", "lv95-source"])
def test_is_in_switzerland_bbox_batch_matches_scalar(source):
    assert is_in_switzerland_bbox_batch(_BATCH_COORDS, source=source) == [
        is_in_switzerland_bbox(cx, cy, source=source) for cx, cy in _BATCH_COORDS
    ]


@pytest.mark.integration
@pytest.mark.parametrize(
    "source, allowed_buffer_km",
    [
        (None, 0),
        (None, 10),
        (CRSType.LV03, 0),
        (CRSType.WGS84, 10),
    ],
    ids=["autodetect", "buffer", "lv03-source", "buffer-and-wgs84-source"],
)
def test_is_in_switzerland_bbox_batch_matches_scalar_across_crs(source, allowed_buffer_km):
    coords = [
        (46.948, 7.447),
        ("46° 56.88' N", "7° 26.82' E"),
        (600_000, 200_000),
        (2_600_000, 1_200_000),
        (46.108565, 5.823456),
        (600_000, 300_000),
        (None, None),
        (48.8566, 2.3522),
    ]
    assert is_in_switzerland_bbox_batch(
        coords,
        allowed_buffer_km=allowed_buffer_km,
        source=source,
    ) == [
        is_in_switzerland_bbox(
            cx,
            cy,
            allowed_buffer_km=allowed_buffer_km,
            source=source,
        )
        for cx, cy in coords
    ]


def test_is_in_switzerland_bbox_batch_invalid_source_raises():
    with pytest.raises(TypeError):
        is_in_switzerland_bbox_batch([(2_600_000, 1_200_000)], source="LV95")


@pytest.mark.parametrize(
    "as_iterable",
    [
        lambda pairs: ((cx, cy) for cx, cy in pairs),
        lambda pairs: zip((p[0] for p in pairs), (p[1] for p in pairs)),
    ],
    ids=["generator", "zip"],
)
def test_is_in_switzerland_bbox_batch_using_iterable(as_iterable):
    expected = [is_in_switzerland_bbox(cx, cy) for cx, cy in _BATCH_COORDS]
    assert is_in_switzerland_bbox_batch(as_iterable(_BATCH_COORDS)) == expected


def test_is_in_switzerland_bbox_batch_explicit_source_skips_detection(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("get_CRS should not run when source is given")

    monkeypatch.setattr("luciole_toolbox.geo.get_CRS", _fail)
    assert is_in_switzerland_bbox_batch(_BATCH_COORDS, source=CRSType.LV95) == [
        is_in_switzerland_bbox(cx, cy, source=CRSType.LV95) for cx, cy in _BATCH_COORDS
    ]
