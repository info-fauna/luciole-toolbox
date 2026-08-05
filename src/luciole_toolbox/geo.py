import re
from enum import Enum


def _parse_coordinate(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace(" ", "").replace("'", "")
        if value == "":
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


# Switzerland and immediate neighbours, decimal degrees. Used to resolve
# which of cx/cy is latitude vs longitude when no hemisphere letter is given
# (the two ranges never overlap, so this also tolerates swapped cx/cy).
_LAT_RANGE = (45.0, 48.5)
_LON_RANGE = (4.5, 11.5)

_DMS_PATTERN = re.compile(
    r"""^\s*
    (?P<deg>\d+(?:\.\d+)?)\s*°\s*
    (?P<min>\d+(?:\.\d+)?)\s*['’′]\s*
    (?:(?P<sec>\d+(?:\.\d+)?)\s*["”″]\s*)?
    (?P<hem>[NSEWnsew])\s*$
    """,
    re.VERBOSE,
)


def _parse_dms(value):
    """Parse '46° 23′ 06.06″ N' into (decimal_degrees, axis); None if not DMS."""
    if not isinstance(value, str):
        return None
    match = _DMS_PATTERN.match(value.strip())
    if match is None:
        return None

    degrees = float(match.group("deg"))
    minutes = float(match.group("min"))
    seconds = float(match.group("sec")) if match.group("sec") else 0.0
    hemisphere = match.group("hem").upper()

    decimal = degrees + minutes / 60 + seconds / 3600
    if hemisphere in ("S", "W"):
        decimal = -decimal

    axis = "lat" if hemisphere in ("N", "S") else "lon"
    return decimal, axis


def _parse_decimal_degree(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
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


# Bern old observatory, origin of the Swiss projection, in arc-seconds.
_ORIGIN_LAT_SEC = 169028.66
_ORIGIN_LON_SEC = 26782.5

# LV03 and LV95 share the exact same projection polynomial and differ only
# in the false easting/northing below. Each target is computed directly from
# WGS84 with its own constants below, rather than deriving one from the
# other via a fixed offset.
_LV_ORIGIN = {
    CRSType.LV03: (600072.37, 200147.07),
    CRSType.LV95: (2600072.37, 1200147.07),
}

_SUPPORTED_TARGETS = tuple(_LV_ORIGIN)


def _wgs84_to_lv(lat, lon, target):
    """Approximate WGS84 -> LV03/LV95 conversion (swisstopo formula, ~1m accuracy)."""
    phi = (lat * 3600 - _ORIGIN_LAT_SEC) / 10000
    lam = (lon * 3600 - _ORIGIN_LON_SEC) / 10000

    easting_origin, northing_origin = _LV_ORIGIN[target]

    easting = (
        easting_origin
        + 211455.93 * lam
        - 10938.51 * lam * phi
        - 0.36 * lam * phi**2
        - 44.54 * lam**3
    )
    northing = (
        northing_origin
        + 308807.95 * phi
        + 3745.25 * lam**2
        + 76.63 * phi**2
        - 194.56 * lam**2 * phi
        + 119.79 * phi**3
    )
    return easting, northing


def convert_coordinates(cx, cy, target=CRSType.LV03):
    """Convert a (cx, cy) pair to `target` (CRSType.LV03 by default).

    Limitation: only WGS84 is supported as a source in this version. Any
    other or unrecognized source - including LV03/LV95 input, since get_CRS
    does not detect those yet - returns None rather than converting.

    An invalid `target` raises ValueError instead of returning None: it is
    a caller configuration mistake, not messy row data, so it should fail
    loudly rather than silently propagate through a pipeline.
    """
    if target not in _SUPPORTED_TARGETS:
        raise ValueError(
            f"convert_coordinates does not support target={target!r}; "
            "only CRSType.LV03/CRSType.LV95 are implemented"
        )

    resolved = _detect_wgs84(cx, cy)
    if resolved is None:
        return None

    lat, lon = resolved
    return _wgs84_to_lv(lat, lon, target)
