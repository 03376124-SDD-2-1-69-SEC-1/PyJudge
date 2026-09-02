"""Topic domain model.

This model deliberately has no FastAPI or database imports. Future modules may
use the same pattern when their own domain vocabulary is agreed.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Topic:
    """A reusable subject classification for programming assignments."""

    id: str
    name: str
    description: str | None
