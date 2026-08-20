import pytest
import requests

from luciole_toolbox.geo import CRSType, LocationInfo, get_location_info

# Bern old observatory area, well within the commune of Bern.
_BERN_LV95 = (2600000, 1200000)
_BERN_WGS84 = (46.9510827718711, 7.43863242087181)

# Vaduz, Liechtenstein: inside the LV95 validity envelope but not part of
# any Swiss canton.
_VADUZ_LV95 = (2758000, 1222000)

# Well outside Switzerland/Liechtenstein (France, west of the Jura).
_OUTSIDE_LV95 = (2470000, 1120000)


@pytest.mark.integration
def test_get_location_info_callable():
    get_location_info(*_BERN_LV95, source=CRSType.LV95)


@pytest.mark.integration
def test_get_location_info_swiss_point():
    result = get_location_info(*_BERN_LV95, source=CRSType.LV95)
    assert result == LocationInfo(cofs=351, commune="Bern", canton="Bern", country="Schweiz")


@pytest.mark.integration
def test_get_location_info_autodetects_source():
    autodetected = get_location_info(*_BERN_LV95)
    explicit = get_location_info(*_BERN_LV95, source=CRSType.LV95)
    assert autodetected == explicit


@pytest.mark.integration
def test_get_location_info_wgs84_input_matches_lv95():
    from_wgs84 = get_location_info(*_BERN_WGS84, source=CRSType.WGS84)
    from_lv95 = get_location_info(*_BERN_LV95, source=CRSType.LV95)
    assert from_wgs84 == from_lv95


@pytest.mark.integration
def test_get_location_info_liechtenstein_point_has_no_canton():
    result = get_location_info(*_VADUZ_LV95, source=CRSType.LV95)
    assert result == LocationInfo(cofs=7001, commune="Vaduz", canton=None, country="Liechtenstein")


@pytest.mark.integration
def test_get_location_info_outside_ch_li_returns_none():
    assert get_location_info(*_OUTSIDE_LV95, source=CRSType.LV95) is None


@pytest.mark.parametrize(
    "cx, cy",
    [
        (None, "1200000"),
        ("2600000", None),
        ("", ""),
        ("impossible", "1200000"),
    ],
    ids=["cx-none", "cy-none", "both-empty", "cx-non-numeric"],
)
def test_get_location_info_unresolvable_coordinates_returns_none(cx, cy):
    assert get_location_info(cx, cy, source=CRSType.LV95) is None


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class _FakeSession:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self._status_code = status_code
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return _FakeResponse(self._payload, self._status_code)


def test_get_location_info_uses_injected_session():
    session = _FakeSession({"results": []})
    assert get_location_info(*_BERN_LV95, source=CRSType.LV95, session=session) is None
    assert len(session.calls) == 1
    _, params, _ = session.calls[0]
    assert params["geometry"] == "2600000,1200000"


def test_get_location_info_propagates_http_errors():
    session = _FakeSession({"results": []}, status_code=500)
    with pytest.raises(requests.HTTPError):
        get_location_info(*_BERN_LV95, source=CRSType.LV95, session=session)
