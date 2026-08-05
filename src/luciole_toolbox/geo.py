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
