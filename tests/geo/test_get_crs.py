import pytest

from luciole_toolbox.geo import CRSType, get_CRS


def test_get_CRS_callable():
    get_CRS(46.385018, 8.044591)


@pytest.mark.parametrize(
    "cx, cy",
    [
        (46.385018, 8.044591),
        ("46.385018", "8.044591"),
    ],
    ids=["floats", "decimal-strings"],
)
def test_get_CRS_decimal_degrees(cx, cy):
    assert get_CRS(cx, cy) == CRSType.WGS84


@pytest.mark.parametrize(
    "cx, cy",
    [
        (8.044591, 46.385018),
    ],
    ids=["decimal-swapped"],
)
def test_get_CRS_decimal_degrees_swapped(cx, cy):
    assert get_CRS(cx, cy) == CRSType.WGS84


@pytest.mark.parametrize(
    "cx, cy",
    [
        ("46° 23′ 06.06″ N", "8° 02′ 40.53″ E"),
        ("8° 02′ 40.53″ E", "46° 23′ 06.06″ N"),
        ("46°23'06.06\"N", "8°02'40.53\"E"),
    ],
    ids=["dms-unicode-symbols", "dms-swapped", "dms-typewriter-symbols"],
)
def test_get_CRS_dms(cx, cy):
    assert get_CRS(cx, cy) == CRSType.WGS84


@pytest.mark.parametrize(
    "cx, cy",
    [
        (90.0, 8.0),
        (46.0, 46.5),
        (8.0, 9.0),
    ],
    ids=["out-of-range", "both-plausible-as-lat-only", "both-plausible-as-lon-only"],
)
def test_get_CRS_unresolvable_axes(cx, cy):
    assert get_CRS(cx, cy) is None


@pytest.mark.parametrize(
    "cx, cy",
    [
        ("2556080", "1206412"),
        ("646614.59", "137252.17"),
    ],
    ids=["lv95-like-not-detected", "lv03-like-not-detected"],
)
def test_get_CRS_planar_not_yet_supported(cx, cy):
    """LV03/LV95 detection is not implemented yet (see get_CRS docstring)."""
    assert get_CRS(cx, cy) is None


@pytest.mark.parametrize(
    "cx, cy",
    [
        (None, "8.044591"),
        ("46.385018", None),
        (None, None),
        ("", "8.044591"),
        ("46.385018", ""),
        ("", ""),
        ("impossible", "8.044591"),
        ("46.385018", "invalid"),
    ],
    ids=[
        "cx-none",
        "cy-none",
        "both-none",
        "cx-empty",
        "cy-empty",
        "both-empty",
        "cx-non-numeric",
        "cy-non-numeric",
    ],
)
def test_get_CRS_invalid_input(cx, cy):
    assert get_CRS(cx, cy) is None


# Real-world input is entered by hand, copy-pasted from maps/GPS units/phones,
# or exported by varied tools - the cases below are all plausible variants a
# user could type.


@pytest.mark.parametrize(
    "cx, cy",
    [
        ("46° 23.101′ N", "8° 02.667′ E"),
        ("46° 23′ 06.06″ n", "8° 02′ 40.53″ e"),
        (46.385018, "8° 02′ 40.53″ E"),
        (" 46.385018 ", "\t8.044591\t"),
        ("+46.385018", "+8.044591"),
        ("46°23′06.06″N", "8°02′40.53″E"),
        ("46,385018", "8,044591"),
        ("46.385018°", "8.044591°"),
        ("46.385018°N", "8.044591°E"),
        ("46.385018N", "8.044591E"),
        ("N 46° 23′ 06.06″", "E 8° 02′ 40.53″"),
        ("46° 23′ 06,06″ N", "8° 02′ 40,53″ E"),
    ],
    ids=[
        "decimal-minutes-no-seconds",
        "lowercase-hemisphere",
        "mixed-decimal-and-dms-columns",
        "padded-whitespace",
        "explicit-plus-sign",
        "unicode-dms-no-spaces",
        "comma-decimal-separator",
        "stray-degree-symbol-no-hemisphere",
        "degree-symbol-and-hemisphere-no-minutes-seconds",
        "hemisphere-glued-no-degree-symbol",
        "prefix-hemisphere",
        "comma-decimal-seconds-in-dms",
    ],
)
def test_get_CRS_diverse_formats(cx, cy):
    assert get_CRS(cx, cy) == CRSType.WGS84
