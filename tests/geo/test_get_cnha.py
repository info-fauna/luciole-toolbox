import pytest

from luciole_toolbox.geo import get_CNHA


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
        ("123", "456", "00010004"),
    ],
    ids=["small-values-zero-padded"],
)
def test_get_CNHA_start_with_0(cx, cy, expected_CNHA):
    assert get_CNHA(cx, cy) == expected_CNHA


@pytest.mark.parametrize(
    "cx, cy, expected_CNHA",
    [
        ("12345678", "98765432", "34567654"),
    ],
    ids=["large-values"],
)
def test_get_CNHA_large_values(cx, cy, expected_CNHA):
    assert get_CNHA(cx, cy) == expected_CNHA


@pytest.mark.parametrize(
    "cx, cy, expected_CNHA",
    [
        ("-2600000", "1200000", "60002000"),
        ("2600000", "-1200000", "60002000"),
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
