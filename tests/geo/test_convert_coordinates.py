import pytest

from luciole_toolbox.geo import CRSType, convert_coordinates

# Bern old observatory: the defining origin of the Swiss projection, so at
# this exact point the polynomial's auxiliary phi'/lambda' are both 0 and
# the formula reduces to the origin constants themselves - no independent
# reference table needed to know the expected output.
_ORIGIN_LAT = 169028.66 / 3600
_ORIGIN_LON = 26782.5 / 3600
_ORIGIN_LV03 = (600072.37, 200147.07)
_ORIGIN_LV95 = (2600072.37, 1200147.07)


@pytest.mark.integration
def test_convert_coordinates_callable():
    convert_coordinates(46.385018, 8.044591)


@pytest.mark.integration
def test_convert_coordinates_default_target_is_LV03():
    assert convert_coordinates(_ORIGIN_LAT, _ORIGIN_LON) == pytest.approx(_ORIGIN_LV03)


@pytest.mark.integration
def test_convert_coordinates_to_LV03():
    result = convert_coordinates(_ORIGIN_LAT, _ORIGIN_LON, target=CRSType.LV03)
    assert result == pytest.approx(_ORIGIN_LV03)


@pytest.mark.integration
def test_convert_coordinates_to_LV95():
    result = convert_coordinates(_ORIGIN_LAT, _ORIGIN_LON, target=CRSType.LV95)
    assert result == pytest.approx(_ORIGIN_LV95)


@pytest.mark.integration
def test_convert_coordinates_dms_input_matches_decimal():
    result = convert_coordinates("46°57'08.66\"N", "7°26'22.50\"E")
    assert result == pytest.approx(_ORIGIN_LV03)


@pytest.mark.integration
def test_convert_coordinates_swapped_columns_match():
    normal = convert_coordinates(46.385018, 8.044591)
    swapped = convert_coordinates(8.044591, 46.385018)
    assert swapped == pytest.approx(normal)


@pytest.mark.integration
def test_convert_coordinates_realistic_point_within_swiss_bounds():
    easting, northing = convert_coordinates(47.3769, 8.5417)
    assert 480_000 < easting < 850_000
    assert 60_000 < northing < 302_000


@pytest.mark.parametrize(
    "cx, cy",
    [
        (None, "8.044591"),
        ("46.385018", None),
        ("", ""),
        ("impossible", "8.044591"),
    ],
    ids=[
        "cx-none",
        "cy-none",
        "both-empty",
        "cx-non-numeric",
    ],
)
def test_convert_coordinates_unresolvable_source_returns_none(cx, cy):
    assert convert_coordinates(cx, cy) is None


def test_convert_coordinates_invalid_target_raises():
    with pytest.raises(ValueError):
        convert_coordinates(46.385018, 8.044591, target="not-a-crs")


@pytest.mark.integration
@pytest.mark.parametrize(
    "cx, cy, source, target",
    [
        ("2556080", "1206412", CRSType.LV95, CRSType.LV03),
        ("646614.59", "137252.17", CRSType.LV03, CRSType.LV95),
    ],
    ids=["lv95-autodetected", "lv03-autodetected"],
)
def test_convert_coordinates_autodetects_lv_source(cx, cy, source, target):
    autodetected = convert_coordinates(cx, cy, target=target)
    explicit = convert_coordinates(cx, cy, target=target, source=source)
    assert autodetected == pytest.approx(explicit)


@pytest.mark.parametrize(
    "cx, cy, source, target, expected",
    [
        ("646614.59", "137252.17", CRSType.LV03, CRSType.LV95, (2646614.59, 1137252.17)),
        (2646614.59, 1137252.17, CRSType.LV95, CRSType.LV03, (646614.84, 137252.48)),
        ("646'614.59", "137'252.17", CRSType.LV03, CRSType.LV95, (2646614.59, 1137252.17)),
    ],
    ids=["lv03-to-lv95", "lv95-to-lv03", "lv03-thousand-separators"],
)
@pytest.mark.integration
def test_convert_coordinates_lv03_lv95_offset(cx, cy, source, target, expected):
    result = convert_coordinates(cx, cy, target=target, source=source)
    assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    "cx, cy, source, target",
    [
        (646614.59, 137252.17, CRSType.LV03, CRSType.LV03),
        (2646614.59, 1137252.17, CRSType.LV95, CRSType.LV95),
    ],
    ids=["lv03-identity", "lv95-identity"],
)
def test_convert_coordinates_lv_identity(cx, cy, source, target):
    assert convert_coordinates(cx, cy, target=target, source=source) == pytest.approx((cx, cy))


@pytest.mark.parametrize(
    "cx, cy",
    [
        (None, "137252.17"),
        ("646614.59", None),
        ("", ""),
        ("impossible", "137252.17"),
    ],
    ids=["cx-none", "cy-none", "both-empty", "cx-non-numeric"],
)
def test_convert_coordinates_lv_invalid_input_returns_none(cx, cy):
    assert convert_coordinates(cx, cy, target=CRSType.LV95, source=CRSType.LV03) is None


# Reference values below are ported verbatim from misc/test_coords_convert.py
# ("les test cases sont corrects et ont ete testes sur Swisstopo"). They are
# kept as-is, not adjusted to whatever this implementation currently
# produces.


@pytest.mark.parametrize(
    "lat, lon, expected",
    [
        (46.427166, 6.101633, (497230.71744352573, 142635.17078830715)),
        (46.481388, 6.113611, (498253.2532867866, 148646.26374590577)),
    ],
    ids=["point-1", "point-2"],
)
@pytest.mark.integration
def test_convert_coordinates_wgs84_to_lv03_reference(lat, lon, expected):
    result = convert_coordinates(lat, lon, target=CRSType.LV03)
    assert result == pytest.approx(expected, rel=1e-5)


@pytest.mark.parametrize(
    "x, y, expected",
    [
        (497230.717, 142635.171, (2497230.717, 1142635.171)),
        (498253.253, 148646.264, (2498253.253, 1148646.264)),
    ],
    ids=["point-1", "point-2"],
)
@pytest.mark.integration
def test_convert_coordinates_lv03_to_lv95_reference(x, y, expected):
    result = convert_coordinates(x, y, target=CRSType.LV95, source=CRSType.LV03)
    assert result == pytest.approx(expected, rel=1e-5)


@pytest.mark.parametrize(
    "x, y, expected",
    [
        (2583097.5, 1212273.0, (47.06126180135882, 7.216140286519122)),
        (2617741.6, 1268431.6, (47.56635386221054, 7.6743795649086755)),
    ],
    ids=["point-1", "point-2"],
)
@pytest.mark.integration
def test_convert_coordinates_lv95_to_wgs84_reference(x, y, expected):
    result = convert_coordinates(x, y, target=CRSType.WGS84, source=CRSType.LV95)
    assert result == pytest.approx(expected, rel=1e-5)
