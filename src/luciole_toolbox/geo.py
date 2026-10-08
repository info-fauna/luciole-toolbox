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


class CRSType(Enum):
    """Define the supported coordinate reference systems (CRS).

    - **WGS84**: Geodetic CRS, EPSG:4326 (lat/lon).
    - **LV03**: Swiss projected CRS, EPSG:21781.
    - **LV95**: Swiss projected CRS, EPSG:2056.
    """

    WGS84 = "WGS84"
    LV03 = "LV03"
    LV95 = "LV95"

    @property
    def epsg(self):
        """Return the EPSG code of this CRS."""
        return _CRS_EPSG[self]

    def round_to_conventional_precision(self, coords):
        """Snap a coordinate pair to this CRS's conventional precision."""
        if coords is None:
            return None

        a, b = coords
        num_decimals = _CRS_DECIMALS[self]
        a = round(a, num_decimals)
        b = round(b, num_decimals)

        if num_decimals == 0:
            a, b = int(a), int(b)

        return a, b

    @classmethod
    def from_epsg_code(cls, epsg_code):
        """Return the CRS corresponding to the given EPSG code."""
        return _EPSG_CRS[epsg_code]


_CRS_EPSG = {
    CRSType.WGS84: "EPSG:4326",
    CRSType.LV03: "EPSG:21781",
    CRSType.LV95: "EPSG:2056",
}
_EPSG_CRS = {epsg_code: crs for crs, epsg_code in _CRS_EPSG.items()}
_CRS_DECIMALS = {
    CRSType.WGS84: 6,
    CRSType.LV03: 0,
    CRSType.LV95: 0,
}

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
# degree/minute/second numbers may use a comma decimal separator. Seconds may
# also be marked by doubling the minute character ('' or ′′) instead of a
# proper double-quote/double-prime (e.g. "46°42'43.72''").
_DMS_PATTERN = re.compile(
    rf"""^\s*
    (?P<hem_pre>[NSEWnsew])?\s*
    (?P<deg>{_NUMBER})\s*[°º]?\s*
    (?:(?P<min>{_NUMBER})\s*['’′]\s*)?
    (?:(?P<sec>{_NUMBER})\s*(?:["”″]|['’′]{{2}})\s*)?
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


def _resolve_wgs84(cx, cy):
    """Return (CRSType.WGS84, lat, lon) if cx/cy jointly form a valid WGS84 pair, else None.

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

    lat, lon = (x_value, y_value) if x_axis == "lat" else (y_value, x_value)

    return CRSType.WGS84, lat, lon


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


def _guess_lv_slot(value, crs=None):
    """Return the (CRSType, axis) slot a planar value unambiguously falls
    into, else None (out of range, or in the gap between two ranges).

    `crs` limits the search to that system's easting and northing ranges.
    """
    slots = _LV_SLOTS.items()
    if crs is not None:
        slots = ((slot, bounds) for slot, bounds in slots if slot[0] == crs)
    matches = [slot for slot, (lo, hi) in slots if lo <= value <= hi]

    return matches[0] if len(matches) == 1 else None


def _resolve_lv(cx, cy, crs=None):
    """Return (crs, easting, northing) if cx/cy jointly form a valid planar
    easting/northing pair in LV03 or LV95, else None. Tolerant of swapped
    cx/cy, same as _detect_wgs84: the pair comes back reordered as
    (easting, northing). If `crs` is given, only that system's ranges are
    considered.
    """
    x = _parse_planar_meters(cx)
    y = _parse_planar_meters(cy)
    if x is None or y is None:
        return None

    x_slot = _guess_lv_slot(x, crs)
    y_slot = _guess_lv_slot(y, crs)
    if x_slot is None or y_slot is None:
        return None

    x_crs, x_axis = x_slot
    y_crs, y_axis = y_slot
    if x_crs != y_crs or x_axis == y_axis:
        return None

    return (x_crs, x, y) if x_axis == "easting" else (x_crs, y, x)


def _resolve_coordinate_pair(cx, cy, source=None) -> tuple[CRSType, float, float] | None:
    """Detect and rearrange the coordinate pair into (crs, a, b), or None if it cannot be resolved.

    `a, b` are in that CRS's own axis order: (easting, northing) for
    LV03/LV95, (lat, lon) for WGS84. Swapped cx/cy
    are reordered. Out-of-range or unrecognized input is None.
    `source` skips auto-detection and resolves the pair in that system only.
    """
    match source:
        case CRSType.WGS84:
            return _resolve_wgs84(cx, cy)
        case CRSType.LV03 | CRSType.LV95:
            return _resolve_lv(cx, cy, crs=source)
        case None:
            resolved = _resolve_wgs84(cx, cy)
            if resolved is None:
                resolved = _resolve_lv(cx, cy)

            return resolved
        case _:
            raise ValueError(f"Invalid `source` value: {source}")


@dataclass(frozen=True)
class GeoPoint:
    """One resolved point, in the CRS it was detected or forced into.

    `a, b` follow that CRS's axis order: (lat, lon) for WGS84,
    (easting, northing) for LV03/LV95. `parse` returns None when the pair
    cannot be resolved. `to` converts on each call; it does not cache.
    """

    crs: CRSType
    a: float
    b: float

    @classmethod
    def parse(cls, cx, cy, source=None) -> GeoPoint | None:
        """Resolve (cx, cy) into a point, or None.

        The coordinate system is auto-detected by default. If the input is unrecognized
        or if the values don't fall within the coordinate system's valid ranges, None
        is returned.
        Swapped coordinates are tolerated.
        The auto-detection is skipped if `source` is given.
        Accepted input is the same as `get_CRS`.
        """
        resolved = _resolve_coordinate_pair(cx, cy, source)
        if resolved is None:
            return None
        crs, a, b = resolved

        return cls(crs, a, b)

    def to(self, target=CRSType.LV03):
        """Return this point in `target`, rounded to that CRS's conventional precision."""
        if self.crs == target:
            result = self.a, self.b
        else:
            result = _get_transformer(self.crs, target).transform(self.a, self.b)

        return target.round_to_conventional_precision(result)

    def get_CKM2(self):
        """6-digit kilometre-square code of this point in LV03.

        Each half is 3 digits, zero-padded, which is the code's defined width.
        """
        easting, northing = self.to(CRSType.LV03)

        return f"{easting // 1000:03d}{northing // 1000:03d}"

    def get_CNHA(self):
        """8-digit hectometre-square code of this point in LV03.

        Each half is 4 digits, zero-padded, which is the code's defined width.
        """
        easting, northing = self.to(CRSType.LV03)

        return f"{easting // 100:04d}{northing // 100:04d}"


def get_CRS(cx: float, cy: float) -> CRSType | None:
    """Detect the coordinate reference system of a (cx, cy) pair: WGS84
    (decimal degrees or DMS, e.g. 46° 23' 06.06" N) or LV03/LV95 (planar
    easting/northing in metres, told apart by their non-overlapping
    magnitude ranges - see _LV_SLOTS). Returns None for any other or
    unrecognized format.
    """
    point = GeoPoint.parse(cx, cy)
    if point is None:
        return None

    return point.crs


def get_CKM2(cx: float, cy: float, source: CRSType | None = None) -> str | None:
    """Return the 6-digit Swiss kilometre-square grid code (3-digit easting
    + 3-digit northing), officially defined on LV03 coordinates.

    The coordinate system is auto-detected by default. If the input is unrecognized
    or if the values don't fall within the coordinate system's valid ranges, None
    is returned.
    Swapped coordinates are tolerated.
    The auto-detection is skipped if `source` is given.
    Accepted input is the same as `get_CRS`.
    """
    point = GeoPoint.parse(cx, cy, source=source)
    if point is None:
        return None

    return point.get_CKM2()


def get_CNHA(cx: float, cy: float, source: CRSType | None = None) -> str | None:
    """Return the 8-digit Swiss hectometre-square grid code (4-digit easting
    + 4-digit northing), officially defined on LV03 coordinates.

    The coordinate system is auto-detected by default. If the input is unrecognized
    or if the values don't fall within the coordinate system's valid ranges, None
    is returned.
    Swapped coordinates are tolerated.
    The auto-detection is skipped if `source` is given.
    Accepted input is the same as `get_CRS`.
    """
    point = GeoPoint.parse(cx, cy, source=source)
    if point is None:
        return None

    return point.get_CNHA()


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


def convert_coordinates(
    cx: float,
    cy: float,
    target: CRSType = CRSType.LV03,
    source: CRSType | None = None,
) -> tuple[int | float, int | float] | None:
    """Convert a (cx, cy) pair to `target` (CRSType.LV03 by default).

    The coordinate system is auto-detected by default. If the input is unrecognized
    or if the values don't fall within the coordinate system's valid ranges, None
    is returned.
    Swapped coordinates are tolerated.
    The auto-detection is skipped if `source` is given.
    Accepted input is the same as `get_CRS`.

    Values are rounded to 0 decimal for LV03 & LV95, 6 decimals for WGS84.
    """
    if not isinstance(source, CRSType | None):
        raise TypeError(f"Invalid `source` value: {source}")
    if not isinstance(target, CRSType):
        raise TypeError(f"Invalid `target` value: {target}")

    point = GeoPoint.parse(cx, cy, source=source)
    if point is None:
        return None

    return point.to(target)


# Switzerland/Liechtenstein bounding box in LV95 - the same figures
# _LV95_EASTING_RANGE/_LV95_NORTHING_RANGE are derived from before widening
# by the neighbour margin, kept separate here since this is a real
# inside/outside check rather than a CRS-detection tolerance.
_CH_LV95_EASTING_RANGE = (2_485_000, 2_834_000)
_CH_LV95_NORTHING_RANGE = (1_075_000, 1_296_000)


def is_in_switzerland_bbox(cx: float, cy: float, source: CRSType | None = None) -> bool | None:
    """Return whether (cx, cy) falls within Switzerland/Liechtenstein's
    bounding box - a fast rectangular approximation, not the precise
    border polygon (see get_location_info for that, at the cost of a
    network call). None is returned if the coordinate could not be parsed
    or detected.

    The coordinate system is auto-detected by default. If the input is unrecognized
    or if the values don't fall within the coordinate system's valid ranges, None
    is returned.
    Swapped coordinates are tolerated.
    The auto-detection is skipped if `source` is given.
    Accepted input is the same as `get_CRS`.
    """
    point = GeoPoint.parse(cx, cy, source=source)
    if point is None:
        return None

    easting, northing = point.to(CRSType.LV95)
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
_SWISSTOPO_POINT_HEIGHT_URL = "https://api3.geo.admin.ch/rest/services/height"

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


def get_location_info(
    cx: float,
    cy: float,
    source: CRSType | None = None,
    session: requests.Session | None = None,
) -> LocationInfo | None:
    """Look up the Swiss/Liechtenstein commune, canton and country a point
    falls in, via swisstopo's public identify API.

    The coordinate system is auto-detected by default. If the input is unrecognized
    or if the values don't fall within the coordinate system's valid ranges, None
    is returned.
    Swapped coordinates are tolerated.
    The auto-detection is skipped if `source` is given.
    Accepted input is the same as `get_CRS`.

    The point is then queried against swisstopo's LV95 administrative-boundary
    layers. Returns None if it falls outside Switzerland/Liechtenstein
    entirely. Network errors from the underlying request propagate to the
    caller rather than being swallowed into a None return, since that would
    be indistinguishable from a point genuinely outside CH/LI.
    """
    point = GeoPoint.parse(cx, cy, source=source)
    if point is None:
        return None

    easting, northing = point.to(CRSType.LV95)
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


def get_altitude(
    cx: float,
    cy: float,
    source: CRSType | None = None,
    session: requests.Session | None = None,
) -> float | None:
    """Look up the DHM25 altitude (metres) of a point, via swisstopo's public
    height API.

    The coordinate system is auto-detected by default. If the input is unrecognized
    or if the values don't fall within the coordinate system's valid ranges, None
    is returned.
    Swapped coordinates are tolerated.
    The auto-detection is skipped if `source` is given.
    Accepted input is the same as `get_CRS`.

    Returns None if the height API rejects the query with an HTTP 400 -
    in practice this means the point falls outside the height model's
    coverage, so like get_location_info, a resolved point with no data is
    None rather than an exception, even though swisstopo signals that case
    as an HTTP 400 here (vs. an empty result set for get_location_info).
    Any other HTTP error still propagates to the caller rather than being
    swallowed.
    """
    point = GeoPoint.parse(cx, cy, source=source)
    if point is None:
        return None

    easting, northing = point.to(CRSType.LV95)
    params = {
        "easting": f"{easting}",
        "northing": f"{northing}",
        "sr": "2056",  # CRSType.LV95
    }
    response = (session or _DEFAULT_SESSION).get(
        _SWISSTOPO_POINT_HEIGHT_URL, params=params, timeout=10
    )
    if response.status_code == 400:
        return None
    response.raise_for_status()

    return float(response.json()["height"])
