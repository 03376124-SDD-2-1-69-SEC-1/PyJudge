"""Averages round half up, unlike Python's round() and "%.1f"."""

from decimal import Decimal

import pytest

from greader.core.rounding import average, half_up


@pytest.mark.parametrize(
    ("value", "expected"),
    [("6.25", 6.3), ("8.45", 8.5), ("7.75", 7.8), ("6.24", 6.2), ("-0.05", -0.1)],
)
def test_half_up(value: str, expected: float) -> None:
    assert half_up(Decimal(value)) == expected


def test_python_rounding_would_have_said_otherwise() -> None:
    assert round(6.25, 1) == 6.2 and f"{8.45:.1f}" == "8.4"


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ([6, 6, 6, 7], 6.3),  # 6.25
        ([8] * 11 + [9] * 9, 8.5),  # 8.45
        ([6, 3, 10], 6.3),  # 6.333...
        ([], None),
    ],
)
def test_average_of_scores(scores: list[int], expected: float | None) -> None:
    assert average(scores) == expected
