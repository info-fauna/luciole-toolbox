from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import pyproj
import requests

# Allows pyproj to fetch the swisstopo NT grid shift files (needed for
# accurate WGS84 <-> LV03/LV95 transformations) from the CDN on first use.
pyproj.network.set_network_enabled(active=True)


def _strip_thousand_separators(value):
    """None passes through unchanged; strings have spaces/apostrophes
    (thousand separators) stripped and are reduced to None if left empty."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace(" ", "").replace("'", "")
        if value == "":
            return None
    return value


def _parse_coordinate(value):
    value = _strip_thousand_separators(value)
    if value is None:
        return None
    try:
        return abs(int(float(value)))
    except (TypeError, ValueError):
        return None


def get_CKM2(cx, cy):
    """Return the 6-digit Swiss kilometre-square grid code (3-digit easting
    + 3-digit northing), officially defined on LV03 coordinates.

    cx/cy are expected in LV03. LV95 is also accepted: its fixed
    +2,000,000/+1,000,000 easting/northing offset over LV03 is stripped via
    `% 1_000_000`, which is only an approximation of the true LV03 value -
    LV95 isn't a pure translation of LV03, so they differ by up to ~1.5 m
    depending on location (see the FINELTRA reframe correction). Close
    enough for a 1 km grid cell; not an exact reprojection. No CRS
    detection is performed - callers needing an exact conversion or WGS84
    support should convert to LV03 via convert_coordinates first.
    """
    x = _parse_coordinate(cx)
    y = _parse_coordinate(cy)

    if x is None or y is None:
        return None

    return f"{x % 1_000_000 // 1000:03d}{y % 1_000_000 // 1000:03d}"


def get_CNHA(cx, cy):
    """Return the 8-digit Swiss hectometre-square grid code (4-digit easting
    + 4-digit northing), officially defined on LV03 coordinates.

    Same LV03/LV95 handling and caveats as get_CKM2 - see that docstring.
    """
    x = _parse_coordinate(cx)
    y = _parse_coordinate(cy)

    if x is None or y is None:
        return None

    return f"{x % 1_000_000 // 100:04d}{y % 1_000_000 // 100:04d}"


class CRSType(Enum):
    WGS84 = "WGS84"
    LV03 = "LV03"
    LV95 = "LV95"

    @property
    def epsg(self):
        return _CRS_EPSG[self]

    @classmethod
    def from_epsg_code(cls, epsg_code):
        return _EPSG_CRS[epsg_code]


_CRS_EPSG = {
    CRSType.WGS84: "EPSG:4326",
    CRSType.LV03: "EPSG:21781",
    CRSType.LV95: "EPSG:2056",
}

_EPSG_CRS = {epsg_code: crs for crs, epsg_code in _CRS_EPSG.items()}

# Switzerland and immediate neighbours, decimal degrees. Used to resolve
# which of cx/cy is latitude vs longitude when no hemisphere letter is given
# (the two ranges never overlap, so this also tolerates swapped cx/cy).
# Derived from the LV95 projection's own validity envelope (pyproj's
# area_of_use is CH+Liechtenstein only) widened by a margin so hand-entered
# points just across the border still resolve.
_NEIGHBOUR_MARGIN_DEG = 1.0
_CH_WEST, _CH_SOUTH, _CH_EAST, _CH_NORTH = pyproj.CRS(CRSType.LV95.epsg).area_of_use.bounds
_LON_RANGE = (_CH_WEST - _NEIGHBOUR_MARGIN_DEG, _CH_EAST + _NEIGHBOUR_MARGIN_DEG)
_LAT_RANGE = (_CH_SOUTH - _NEIGHBOUR_MARGIN_DEG, _CH_NORTH + _NEIGHBOUR_MARGIN_DEG)

_NUMBER = r"\d+(?:[.,]\d+)?"

# Hemisphere may be a prefix ("N 46...") or a suffix ("...46 N"), the degree
# symbol and the minute/second parts are all optional (covers a bare
# "46.38N" as well as DM - decimal minutes, no seconds - and full DMS), and
# degree/minute/second numbers may use a comma decimal separator.
_DMS_PATTERN = re.compile(
    rf"""^\s*
    (?P<hem_pre>[NSEWnsew])?\s*
    (?P<deg>{_NUMBER})\s*[°º]?\s*
    (?:(?P<min>{_NUMBER})\s*['’′]\s*)?
    (?:(?P<sec>{_NUMBER})\s*["”″]\s*)?
    (?P<hem_post>[NSEWnsew])?\s*$
    """,
    re.VERBOSE,
)


def _parse_dms(value):
    """Parse a degrees/minutes/seconds value into (decimal_degrees, axis).
    A hemisphere letter ('46° 23′ 06.06″ N', 'N46.38', '8° 02.5′ E') fixes
    the sign and the axis; without one ('46°00′49.13″') the value is
    assumed positive and axis is None, left for the caller to resolve (e.g.
    via magnitude, as `_detect_wgs84` already does for plain decimals).
    None is returned if the value doesn't look like DMS at all, or carries
    contradictory hemisphere letters on both ends.
    """
    if not isinstance(value, str):
        return None
    match = _DMS_PATTERN.match(value.strip())
    if match is None:
        return None

    hem_pre = match.group("hem_pre")
    hem_post = match.group("hem_post")
    if hem_pre and hem_post:
        return None
    hemisphere = hem_pre or hem_post
    if hemisphere is not None:
        hemisphere = hemisphere.upper()

    def _num(group_name):
        raw = match.group(group_name)
        return float(raw.replace(",", ".")) if raw else 0.0

    decimal = _num("deg") + _num("min") / 60 + _num("sec") / 3600
    if hemisphere in ("S", "W"):
        decimal = -decimal

    axis = None
    if hemisphere is not None:
        axis = "lat" if hemisphere in ("N", "S") else "lon"
    return decimal, axis


def _parse_decimal_degree(value):
    """Parse a plain decimal degree, no hemisphere letter: '46.385018',
    '46,385018' (comma decimal separator), and '46.385018°' (stray degree
    symbol, no hemisphere) are all accepted.
    """
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if text.endswith(("°", "º")):
            text = text[:-1].strip()
        if text == "":
            return None
        try:
            return float(text)
        except ValueError:
            pass
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _guess_axis(value):
    lat_min, lat_max = _LAT_RANGE
    lon_min, lon_max = _LON_RANGE
    in_lat = lat_min <= value <= lat_max
    in_lon = lon_min <= value <= lon_max
    if in_lat and not in_lon:
        return "lat"
    if in_lon and not in_lat:
        return "lon"
    return None


def _parse_wgs84_component(raw):
    """Return (value, axis) where axis is 'lat'/'lon' (from a DMS hemisphere
    letter) or None (plain decimal, or hemisphere-less DMS - axis not yet
    known)."""
    dms = _parse_dms(raw)
    if dms is not None:
        return dms

    decimal = _parse_decimal_degree(raw)
    if decimal is None:
        return None
    return decimal, None


def _detect_wgs84(cx, cy):
    """Return (lat, lon) if cx/cy jointly form a valid WGS84 pair, else None.

    Tolerant of swapped cx/cy: axis is read from the DMS hemisphere letter
    when present, otherwise resolved from the (non-overlapping) lat/lon
    ranges above.
    """
    x = _parse_wgs84_component(cx)
    y = _parse_wgs84_component(cy)
    if x is None or y is None:
        return None

    x_value, x_axis = x
    y_value, y_axis = y

    if x_axis is None:
        x_axis = _guess_axis(x_value)
    if y_axis is None:
        y_axis = _guess_axis(y_value)

    if x_axis is None or y_axis is None or x_axis == y_axis:
        return None

    return (x_value, y_value) if x_axis == "lat" else (y_value, x_value)


# Native LV03/LV95 easting/northing bounds (metres), per swisstopo's
# published validity envelope for each projection, widened by a margin so
# hand-entered points just across the border still resolve. LV95 offsets
# LV03 by a fixed +2,000,000 (easting) / +1,000,000 (northing), so the four
# ranges below never overlap - this lets a value's magnitude alone say
# which system and axis it belongs to, and (like _detect_wgs84) tolerates
# swapped cx/cy for free.
_LV_NEIGHBOUR_MARGIN_M = 50_000
_LV03_EASTING_RANGE = (485_000 - _LV_NEIGHBOUR_MARGIN_M, 834_000 + _LV_NEIGHBOUR_MARGIN_M)
_LV03_NORTHING_RANGE = (75_000 - _LV_NEIGHBOUR_MARGIN_M, 296_000 + _LV_NEIGHBOUR_MARGIN_M)
_LV95_EASTING_RANGE = (2_485_000 - _LV_NEIGHBOUR_MARGIN_M, 2_834_000 + _LV_NEIGHBOUR_MARGIN_M)
_LV95_NORTHING_RANGE = (1_075_000 - _LV_NEIGHBOUR_MARGIN_M, 1_296_000 + _LV_NEIGHBOUR_MARGIN_M)

_LV_SLOTS = {
    (CRSType.LV03, "easting"): _LV03_EASTING_RANGE,
    (CRSType.LV03, "northing"): _LV03_NORTHING_RANGE,
    (CRSType.LV95, "easting"): _LV95_EASTING_RANGE,
    (CRSType.LV95, "northing"): _LV95_NORTHING_RANGE,
}


def _guess_lv_slot(value):
    """Return the (CRSType, axis) slot a planar value unambiguously falls
    into, else None (out of range, or in the gap between two ranges)."""
    matches = [slot for slot, (lo, hi) in _LV_SLOTS.items() if lo <= value <= hi]
    return matches[0] if len(matches) == 1 else None


def _detect_lv(cx, cy):
    """Return CRSType.LV03 or CRSType.LV95 if cx/cy jointly form a valid
    planar easting/northing pair in that system, else None. Tolerant of
    swapped cx/cy, same as _detect_wgs84."""
    x = _parse_planar_meters(cx)
    y = _parse_planar_meters(cy)
    if x is None or y is None:
        return None

    x_slot = _guess_lv_slot(x)
    y_slot = _guess_lv_slot(y)
    if x_slot is None or y_slot is None:
        return None

    x_crs, x_axis = x_slot
    y_crs, y_axis = y_slot
    if x_crs != y_crs or x_axis == y_axis:
        return None

    return x_crs


def get_CRS(cx, cy):
    """Detect the coordinate reference system of a (cx, cy) pair: WGS84
    (decimal degrees or DMS, e.g. 46° 23' 06.06" N) or LV03/LV95 (planar
    easting/northing in metres, told apart by their non-overlapping
    magnitude ranges - see _LV_SLOTS). Returns None for any other or
    unrecognized format.
    """
    if _detect_wgs84(cx, cy) is not None:
        return CRSType.WGS84
    return _detect_lv(cx, cy)


_SUPPORTED_TARGETS = tuple(CRSType)

# Cached per (source, target) pair - building a Transformer parses the grid
# shift files, so it's worth not repeating on every call.
_TRANSFORMERS = {}


def _get_transformer(source, target):
    key = (source, target)
    if key not in _TRANSFORMERS:
        # always_xy=False keeps each CRS's own defined axis order: (lat, lon)
        # for EPSG:4326, (easting, northing) for EPSG:21781/2056 - which is
        # exactly the order this module already parses/returns, so no manual
        # reordering is needed here.
        _TRANSFORMERS[key] = pyproj.Transformer.from_crs(source.epsg, target.epsg, always_xy=False)
    return _TRANSFORMERS[key]


def _parse_planar_meters(value):
    value = _strip_thousand_separators(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _convert_lv(cx, cy, source, target):
    x = _parse_planar_meters(cx)
    y = _parse_planar_meters(cy)
    if x is None or y is None:
        return None

    if source == target:
        return x, y

    return _get_transformer(source, target).transform(x, y)


def convert_coordinates(cx, cy, target=CRSType.LV03, source=None):
    """Convert a (cx, cy) pair to `target` (CRSType.LV03 by default).

    `source` may be given explicitly as CRSType.WGS84/LV03/LV95 to skip
    detection. Left at its default (None), it is auto-detected via
    get_CRS; unrecognized input returns None rather than converting.

    An invalid `target` raises ValueError instead of returning None: it is
    a caller configuration mistake, not messy row data, so it should fail
    loudly rather than silently propagate through a pipeline.
    """
    if target not in _SUPPORTED_TARGETS:
        raise ValueError(
            f"convert_coordinates does not support target={target!r}; "
            "only CRSType.LV03/CRSType.LV95/CRSType.WGS84 are implemented"
        )

    source = source or get_CRS(cx, cy)

    if source in (CRSType.LV03, CRSType.LV95):
        return _convert_lv(cx, cy, source, target)

    if source == CRSType.WGS84:
        resolved = _detect_wgs84(cx, cy)
        if resolved is None:
            return None
        lat, lon = resolved
        return _get_transformer(CRSType.WGS84, target).transform(lat, lon)

    return None


# Switzerland/Liechtenstein bounding box in LV95 - the same figures
# _LV95_EASTING_RANGE/_LV95_NORTHING_RANGE are derived from before widening
# by the neighbour margin, kept separate here since this is a real
# inside/outside check rather than a CRS-detection tolerance.
_CH_LV95_EASTING_RANGE = (2_485_000, 2_834_000)
_CH_LV95_NORTHING_RANGE = (1_075_000, 1_296_000)


def is_in_switzerland_bbox(cx, cy, source=None):
    """Return whether (cx, cy) falls within Switzerland/Liechtenstein's
    bounding box - a fast rectangular approximation, not the precise
    border polygon (see get_location_info for that, at the cost of a
    network call).

    Accepts the same input as convert_coordinates: WGS84 (decimal degrees
    or DMS), LV03 or LV95, auto-detected unless `source` is given
    explicitly. Returns None if the coordinate can't be parsed/detected at
    all, so callers can tell "unrecognized input" apart from "recognized
    but outside the box" instead of both reading as one falsy value.
    """
    coords = convert_coordinates(cx, cy, target=CRSType.LV95, source=source)
    if coords is None:
        return None
    easting, northing = coords

    east_min, east_max = _CH_LV95_EASTING_RANGE
    north_min, north_max = _CH_LV95_NORTHING_RANGE
    return east_min <= easting <= east_max and north_min <= northing <= north_max


@dataclass(frozen=True)
class LocationInfo:
    """Administrative context of a point: BFS/OFS commune number (COFS),
    commune, canton and country. Names are exactly as published by
    swisstopo, not translated by this module - the country name comes out
    German ("Schweiz", "Liechtenstein"), commune/canton names in their own
    official language. `canton` is None for a Liechtenstein point, since it
    isn't part of the Swiss canton system.
    """

    cofs: int | None
    commune: str | None
    canton: str | None
    country: str | None


# Public read-only API - no key required. See
# https://api3.geo.admin.ch/services/sdiservices.html#identify-features
_SWISSTOPO_IDENTIFY_URL = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
_SWISSTOPO_LAND_LAYER = "ch.swisstopo.swissboundaries3d-land-flaeche.fill"
_SWISSTOPO_KANTON_LAYER = "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill"
_SWISSTOPO_GEMEINDE_LAYER = "ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill"

# Reused across calls instead of opening a new connection every time -
# callers needing custom auth/timeouts/retries can pass their own session.
_DEFAULT_SESSION = requests.Session()


def _identify_by_layer(easting, northing, session):
    params = {
        "geometry": f"{easting},{northing}",
        "geometryType": "esriGeometryPoint",
        "sr": 2056,
        "layers": (
            f"all:{_SWISSTOPO_LAND_LAYER},{_SWISSTOPO_KANTON_LAYER},{_SWISSTOPO_GEMEINDE_LAYER}"
        ),
        "tolerance": 0,
        "mapExtent": f"{easting},{northing},{easting},{northing}",
        "imageDisplay": "1,1,96",
        "returnGeometry": "false",
    }
    response = (session or _DEFAULT_SESSION).get(_SWISSTOPO_IDENTIFY_URL, params=params, timeout=10)
    response.raise_for_status()

    by_layer = {}
    for result in response.json()["results"]:
        by_layer.setdefault(result["layerBodId"], []).append(result["attributes"])
    return by_layer


def get_location_info(cx, cy, source=None, session=None):
    """Look up the Swiss/Liechtenstein commune, canton and country a point
    falls in, via swisstopo's public identify API.

    cx/cy are detected/converted the same way as convert_coordinates
    (`source` skips detection); the point is then queried against
    swisstopo's LV95 administrative-boundary layers. Returns None if the
    coordinate can't be resolved, or falls outside Switzerland/Liechtenstein
    entirely. Network errors from the underlying request propagate to the
    caller rather than being swallowed into a None return, since that would
    be indistinguishable from a point genuinely outside CH/LI.
    """
    coords = convert_coordinates(cx, cy, target=CRSType.LV95, source=source)
    if coords is None:
        return None
    easting, northing = coords

    by_layer = _identify_by_layer(easting, northing, session)

    land = by_layer.get(_SWISSTOPO_LAND_LAYER)
    if not land:
        return None
    country = land[0]["bez"]

    kanton = by_layer.get(_SWISSTOPO_KANTON_LAYER)
    canton = kanton[0]["name"] if kanton else None

    current_gemeinde = next(
        (g for g in by_layer.get(_SWISSTOPO_GEMEINDE_LAYER, []) if g["is_current_jahr"]),
        None,
    )
    cofs = current_gemeinde["gde_nr"] if current_gemeinde else None
    commune = current_gemeinde["gemname"] if current_gemeinde else None

    return LocationInfo(cofs=cofs, commune=commune, canton=canton, country=country)
