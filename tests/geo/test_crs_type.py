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
