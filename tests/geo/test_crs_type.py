import pytest

from luciole_toolbox.geo import CRSType


@pytest.mark.parametrize(
    "crs, expected_epsg",
    [
        (CRSType.WGS84, "EPSG:4326"),
        (CRSType.LV03, "EPSG:21781"),
        (CRSType.LV95, "EPSG:2056"),
    ],
    ids=["wgs84", "lv03", "lv95"],
)
def test_epsg(crs, expected_epsg):
    assert crs.epsg == expected_epsg


@pytest.mark.parametrize(
    "epsg_code, expected_crs",
    [
        ("EPSG:4326", CRSType.WGS84),
        ("EPSG:21781", CRSType.LV03),
        ("EPSG:2056", CRSType.LV95),
    ],
    ids=["wgs84", "lv03", "lv95"],
)
def test_from_epsg_code(epsg_code, expected_crs):
    assert CRSType.from_epsg_code(epsg_code) == expected_crs


@pytest.mark.parametrize("crs", list(CRSType), ids=lambda crs: crs.name)
def test_from_epsg_code_roundtrips_epsg(crs):
    assert CRSType.from_epsg_code(crs.epsg) == crs


def test_from_epsg_code_unknown_raises_key_error():
    with pytest.raises(KeyError):
        CRSType.from_epsg_code("EPSG:9999")


@pytest.mark.parametrize(
    "crs, source_coords, expected_coords",
    [
        (CRSType.WGS84, (46.765, 7.432), (46.765, 7.432)),
        (CRSType.WGS84, (46.9524038, 7.4395827), (46.952404, 7.439583)),
        (CRSType.LV03, (600000, 200000), (600000, 200000)),
        (CRSType.LV03, (600000.054, 200000.007), (600000, 200000)),
        (CRSType.LV95, (2500000, 1075000), (2500000, 1075000)),
        (CRSType.LV95, (2500000.054, 1075000.007), (2500000, 1075000)),
    ],
    ids=["wgs84_1", "wgs84_2", "lv03_1", "lv03_2", "lv95_1", "lv95_2"],
)
def test_round_to_conventional_precision(crs, source_coords, expected_coords):
    assert crs.round_to_conventional_precision(source_coords) == expected_coords
