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


def test_convert_coordinates_callable():
    convert_coordinates(46.385018, 8.044591)


def test_convert_coordinates_default_target_is_LV03():
    assert convert_coordinates(_ORIGIN_LAT, _ORIGIN_LON) == pytest.approx(_ORIGIN_LV03)


def test_convert_coordinates_to_LV03():
    result = convert_coordinates(_ORIGIN_LAT, _ORIGIN_LON, target=CRSType.LV03)
    assert result == pytest.approx(_ORIGIN_LV03)


def test_convert_coordinates_to_LV95():
    result = convert_coordinates(_ORIGIN_LAT, _ORIGIN_LON, target=CRSType.LV95)
    assert result == pytest.approx(_ORIGIN_LV95)


def test_convert_coordinates_dms_input_matches_decimal():
    result = convert_coordinates("46°57'08.66\"N", "7°26'22.50\"E")
    assert result == pytest.approx(_ORIGIN_LV03)


def test_convert_coordinates_swapped_columns_match():
    normal = convert_coordinates(46.385018, 8.044591)
    swapped = convert_coordinates(8.044591, 46.385018)
    assert swapped == pytest.approx(normal)


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
        ("2556080", "1206412"),
    ],
    ids=[
        "cx-none",
        "cy-none",
        "both-empty",
        "cx-non-numeric",
        "planar-not-yet-supported",
    ],
)
def test_convert_coordinates_unresolvable_source_returns_none(cx, cy):
    assert convert_coordinates(cx, cy) is None


def test_convert_coordinates_invalid_target_raises():
    with pytest.raises(ValueError):
        convert_coordinates(46.385018, 8.044591, target=CRSType.WGS84)
