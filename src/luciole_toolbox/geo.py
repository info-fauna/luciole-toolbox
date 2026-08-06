import re
from enum import Enum

import pyproj

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
    x = _parse_coordinate(cx)
    y = _parse_coordinate(cy)

    if x is None or y is None:
        return None

    return f"{x % 1_000_000 // 1000:03d}{y % 1_000_000 // 1000:03d}"


def get_CNHA(cx, cy):
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


_CRS_EPSG = {
    CRSType.WGS84: "EPSG:4326",
    CRSType.LV03: "EPSG:21781",
    CRSType.LV95: "EPSG:2056",
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
    """Parse a hemisphere-annotated value - '46° 23′ 06.06″ N', 'N46.38',
    '8° 02.5′ E' - into (decimal_degrees, axis). None if no hemisphere
    letter is present (not this format) or two are (contradictory input).
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
    if hemisphere is None:
        return None
    hemisphere = hemisphere.upper()

    def _num(group_name):
        raw = match.group(group_name)
        return float(raw.replace(",", ".")) if raw else 0.0

    decimal = _num("deg") + _num("min") / 60 + _num("sec") / 3600
    if hemisphere in ("S", "W"):
        decimal = -decimal

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
    letter) or None (plain decimal, axis not yet known)."""
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


def get_CRS(cx, cy):
    """Detect the coordinate reference system of a (cx, cy) pair.

    Limitation: only WGS84 (decimal degrees or DMS, e.g. 46° 23' 06.06" N)
    is currently detected. LV03/LV95 planar detection is not implemented
    yet; such input returns None, same as any other unrecognized format.
    """
    if _detect_wgs84(cx, cy) is not None:
        return CRSType.WGS84
    return None


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
        _TRANSFORMERS[key] = pyproj.Transformer.from_crs(
            source.epsg, target.epsg, always_xy=False
        )
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

    `source` may be given explicitly as CRSType.LV03 or CRSType.LV95 to
    convert directly from a planar system to any target (the other planar
    system or WGS84) - get_CRS does not detect LV03/LV95 sources yet, so
    this can't be auto-detected. Left at its default (None), the source is
    auto-detected and only WGS84 is recognized; any other or unrecognized
    source returns None rather than converting.

    An invalid `target` raises ValueError instead of returning None: it is
    a caller configuration mistake, not messy row data, so it should fail
    loudly rather than silently propagate through a pipeline.
    """
    if target not in _SUPPORTED_TARGETS:
        raise ValueError(
            f"convert_coordinates does not support target={target!r}; "
            "only CRSType.LV03/CRSType.LV95/CRSType.WGS84 are implemented"
        )

    if source in (CRSType.LV03, CRSType.LV95):
        return _convert_lv(cx, cy, source, target)

    resolved = _detect_wgs84(cx, cy)
    if resolved is None:
        return None

    lat, lon = resolved
    return _get_transformer(CRSType.WGS84, target).transform(lat, lon)
