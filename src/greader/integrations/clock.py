"""The wall clock, as the Clock Protocol the slices depend on."""

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
