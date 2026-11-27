import pytest

from luciole_toolbox.geo import CRSType, get_CNHA, get_CNHA_batch


def test_get_CNHA_callable():
    get_CNHA(0, 0)


@pytest.mark.parametrize(
    "cx, cy, expected_CNHA",
    [
        ("2556080", "1206412", "55602064"),
        ("2600123", "1200456", "60012004"),
    ],
    ids=["standard-1", "standard-2"],
)
def test_get_CNHA_standard(cx, cy, expected_CNHA):
    assert get_CNHA(cx, cy) == expected_CNHA


@pytest.mark.parametrize(
    "cx, cy, expected_CNHA",
    [
        ("2556080.444", "1206412.44", "55602064"),
    ],
    ids=["decimal-values"],
)
def test_get_CNHA_decimal_input(cx, cy, expected_CNHA):
    assert get_CNHA(cx, cy) == expected_CNHA


@pytest.mark.parametrize(
    "cx, cy, expected_CNHA",
    [
        ("2 600 000", "1'200'000", "60002000"),
    ],
    ids=["spaces-and-thousand-separators"],
)
def test_get_CNHA_formatted_input(cx, cy, expected_CNHA):
    assert get_CNHA(cx, cy) == expected_CNHA


@pytest.mark.parametrize(
    "cx, cy, expected_CNHA",
    [
        (45.822194, 9.012894, "72230757"),
    ],
    ids=["small-values-zero-padded"],
)
def test_get_CNHA_start_with_0(cx, cy, expected_CNHA):
    """
    South locations will have less digits if not padded. For
    example 45.822194, 9.012894 (near Chiasso) will return
    7223757 instead of 72230757. This test ensures that the
    result is padded so that the result is always 8 digits.
    """
    assert get_CNHA(cx, cy) == expected_CNHA


@pytest.mark.parametrize(
    "cx, cy, expected_CNHA",
    [
        ("12345678", "98765432", None),
    ],
    ids=["large-values"],
)
def test_get_CNHA_large_values(cx, cy, expected_CNHA):
    assert get_CNHA(cx, cy) == expected_CNHA


@pytest.mark.parametrize(
    "cx, cy, expected_CNHA",
    [
        ("-2600000", "1200000", None),
        ("2600000", "-1200000", None),
    ],
    ids=["negative-cx", "negative-cy"],
)
def test_get_CNHA_negative_values(cx, cy, expected_CNHA):
    assert get_CNHA(cx, cy) == expected_CNHA


@pytest.mark.parametrize(
    "cx, cy",
    [
        (None, "1200000"),
        ("2600000", None),
        (None, None),
        ("", "1200000"),
        ("2600000", ""),
        ("", ""),
        ("impossible", "1200000"),
        ("2600000", "invalid"),
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
def test_get_CNHA_text(cx, cy):
    assert get_CNHA(cx, cy) is None


_BATCH_COORDS = [
    ("2556080", "1206412"),
    ("2600123", "1200456"),
    ("2556080.444", "1206412.44"),
    ("2 600 000", "1'200'000"),
    (45.822194, 9.012894),
    ("12345678", "98765432"),
    ("-2600000", "1200000"),
    (None, "1200000"),
    ("", ""),
    ("2556080", "1206412"),
]


def test_get_CNHA_batch_empty():
    assert get_CNHA_batch([]) == []


def test_get_CNHA_batch_string_raises():
    with pytest.raises(TypeError):
        get_CNHA_batch("2556080, 1206412")


@pytest.mark.parametrize("source", [None, *CRSType], ids=["autodetect", "wgs84", "lv03", "lv95"])
def test_get_CNHA_batch_matches_get_CNHA(source):
    assert get_CNHA_batch(_BATCH_COORDS, source=source) == [
        get_CNHA(cx, cy, source=source) for cx, cy in _BATCH_COORDS
    ]


def test_get_CNHA_batch_invalid_source_raises():
    with pytest.raises(TypeError):
        get_CNHA_batch([("2556080", "1206412")], source="LV95")


@pytest.mark.parametrize(
    "as_iterable",
    [
        lambda pairs: ((cx, cy) for cx, cy in pairs),
        lambda pairs: zip((p[0] for p in pairs), (p[1] for p in pairs)),
    ],
    ids=["generator", "zip"],
)
def test_get_CNHA_batch_using_iterable(as_iterable):
    expected = [get_CNHA(cx, cy) for cx, cy in _BATCH_COORDS]
    assert get_CNHA_batch(as_iterable(_BATCH_COORDS)) == expected


def test_get_CNHA_batch_explicit_source_skips_detection(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("get_CRS should not run when source is given")

    monkeypatch.setattr("luciole_toolbox.geo.get_CRS", _fail)
    assert get_CNHA_batch(_BATCH_COORDS, source=CRSType.LV03) == [
        get_CNHA(cx, cy, source=CRSType.LV03) for cx, cy in _BATCH_COORDS
    ]
