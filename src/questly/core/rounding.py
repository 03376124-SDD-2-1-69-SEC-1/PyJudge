"""Rounding shown to people: half up, never Python's round-half-to-even.

`round(6.25, 1)` is 6.2 and `"%.1f" % 6.25` is "6.2"; a teacher reads 6.25
as 6.3. Averages are computed in Decimal from the scores themselves, so a
float sum such as 8.4499999 cannot tip the result either way.
"""

from decimal import ROUND_HALF_UP, Decimal


def half_up(value: Decimal, places: int = 1) -> float:
    step = Decimal(1).scaleb(-places)
    return float(value.quantize(step, rounding=ROUND_HALF_UP))


def average(values: list[int] | list[float], places: int = 1) -> float | None:
    """Mean rounded half up to `places` decimals; None when there is nothing."""
    if not values:
        return None
    total = sum((Decimal(str(value)) for value in values), Decimal(0))
    return half_up(total / len(values), places)
