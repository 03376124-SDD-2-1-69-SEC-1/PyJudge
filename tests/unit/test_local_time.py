from datetime import UTC, datetime

from questly.main import local_time


def test_local_time_formats_unpadded_day_portably() -> None:
    value = datetime(2026, 10, 8, 20, 5, tzinfo=UTC)

    assert local_time(value) == "9 Oct, 03:05"
    assert local_time(value, "%-d %b") == "9 Oct"


def test_local_time_keeps_zero_padded_day_when_requested() -> None:
    value = datetime(2026, 10, 8, 20, 5, tzinfo=UTC)

    assert local_time(value, "%d %b") == "09 Oct"
