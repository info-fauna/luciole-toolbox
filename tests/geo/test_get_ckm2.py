import pytest

from luciole_toolbox.geo import get_CKM2


def test_get_CKM2_callable():
    get_CKM2(0, 0)


@pytest.mark.parametrize(
    "cx, cy, expected_CKM2",
    [
        ("2556080", "1206412", "556206"),
        ("2600123", "1200456", "600200"),
    ],
    ids=["standard-1", "standard-2"],
)
def test_get_CKM2_standard(cx, cy, expected_CKM2):
    assert get_CKM2(cx, cy) == expected_CKM2


@pytest.mark.parametrize(
    "cx, cy, expected_CKM2",
    [
        ("2556080.444", "1206412.44", "556206"),
    ],
    ids=["decimal-values"],
)
def test_get_CKM2_decimal_input(cx, cy, expected_CKM2):
    assert get_CKM2(cx, cy) == expected_CKM2


@pytest.mark.parametrize(
    "cx, cy, expected_CKM2",
    [
        ("2 600 000", "1'200'000", "600200"),
    ],
    ids=["spaces-and-thousand-separators"],
)
def test_get_CKM2_formatted_input(cx, cy, expected_CKM2):
    assert get_CKM2(cx, cy) == expected_CKM2


@pytest.mark.parametrize(
    "cx, cy, expected_CKM2",
    [
        ("123", "456", "000000"),
    ],
    ids=["small-values-zero-padded"],
)
def test_get_CKM2_start_with_0(cx, cy, expected_CKM2):
    assert get_CKM2(cx, cy) == expected_CKM2


@pytest.mark.parametrize(
    "cx, cy, expected_CKM2",
    [
        ("12345678", "98765432", "345765"),
    ],
    ids=["large-values"],
)
def test_get_CKM2_large_values(cx, cy, expected_CKM2):
    assert get_CKM2(cx, cy) == expected_CKM2


@pytest.mark.parametrize(
    "cx, cy, expected_CKM2",
    [
        ("-2600000", "1200000", "600200"),
        ("2600000", "-1200000", "600200"),
    ],
    ids=["negative-cx", "negative-cy"],
)
def test_get_CKM2_negative_values(cx, cy, expected_CKM2):
    assert get_CKM2(cx, cy) == expected_CKM2


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
def test_get_CKM2_text(cx, cy):
    assert get_CKM2(cx, cy) is None
