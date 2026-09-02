import pytest
import requests

from luciole_toolbox.geo import CRSType, get_altitude

# Bern old observatory area. DHM25 height is stable over time, safe to
# hardcode for an integration assertion.
_BERN_LV95 = (2600000, 1200000)
_BERN_WGS84 = (46.9510827718711, 7.43863242087181)
_BERN_HEIGHT = 555.5

# Well outside the DHM25 model's coverage - the height service itself
# rejects the query (400), unlike get_location_info which just finds no
# matching boundary.
_OUT_OF_BOUNDS_LV95 = (0, 0)


@pytest.mark.integration
def test_get_altitude_callable():
    get_altitude(*_BERN_LV95, source=CRSType.LV95)


@pytest.mark.integration
def test_get_altitude_swiss_point():
    assert get_altitude(*_BERN_LV95, source=CRSType.LV95) == _BERN_HEIGHT


@pytest.mark.integration
def test_get_altitude_autodetects_source():
    autodetected = get_altitude(*_BERN_LV95)
    explicit = get_altitude(*_BERN_LV95, source=CRSType.LV95)
    assert autodetected == explicit


@pytest.mark.integration
def test_get_altitude_wgs84_input_matches_lv95():
    from_wgs84 = get_altitude(*_BERN_WGS84, source=CRSType.WGS84)
    from_lv95 = get_altitude(*_BERN_LV95, source=CRSType.LV95)
    assert from_wgs84 == from_lv95


@pytest.mark.integration
def test_get_altitude_out_of_bounds_raises_http_error():
    with pytest.raises(requests.HTTPError):
        get_altitude(*_OUT_OF_BOUNDS_LV95, source=CRSType.LV95)


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
def test_get_altitude_unresolvable_coordinates_returns_none(cx, cy):
    assert get_altitude(cx, cy, source=CRSType.LV95) is None


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


def test_get_altitude_uses_injected_session():
    session = _FakeSession({"height": "555.5"})
    assert get_altitude(*_BERN_LV95, source=CRSType.LV95, session=session) == 555.5
    assert len(session.calls) == 1
    _, params, _ = session.calls[0]
    assert params["easting"] == "2600000"
    assert params["northing"] == "1200000"
    assert params["sr"] == "2056"


def test_get_altitude_propagates_http_errors():
    session = _FakeSession({}, status_code=500)
    with pytest.raises(requests.HTTPError):
        get_altitude(*_BERN_LV95, source=CRSType.LV95, session=session)
