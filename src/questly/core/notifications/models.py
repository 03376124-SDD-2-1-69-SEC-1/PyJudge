"""Domain model for user notifications."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Notification:
    """A notification belonging to one user."""

    user_id: int
    kind: str
    payload: dict[str, str | int | bool | None]
    created_at: datetime
    id: int | None = None
    read_at: datetime | None = None
