"""The `|local` template filter, whose `%-d` must work on Windows too.

Windows strftime has no `%-d` (it raises ValueError), so local_time swaps it
for the unpadded day itself. Credit: Nat (e42da20).
"""

from datetime import UTC, datetime

from questly.main import local_time


class WindowsDatetime(datetime):
    """Refuses `%-` directives the way the Windows C runtime does."""

    def strftime(self, pattern: str) -> str:
        if "%-" in pattern:
            raise ValueError("Invalid format string")
        return super().strftime(pattern)


def test_dash_d_renders_the_unpadded_day_where_strftime_lacks_it() -> None:
    value = WindowsDatetime(2026, 9, 4, 3, 5, tzinfo=UTC)

    assert local_time(value, "%-d %b") == "4 Sep"


def test_default_pattern_uses_bangkok_time_across_midnight() -> None:
    late_utc = WindowsDatetime(2026, 9, 30, 18, 30, tzinfo=UTC)

    assert local_time(late_utc) == "1 Oct, 01:30"


def test_pattern_without_dash_d_is_passed_through() -> None:
    assert local_time(datetime(2026, 9, 4, 3, 5, tzinfo=UTC), "%d/%m") == "04/09"
