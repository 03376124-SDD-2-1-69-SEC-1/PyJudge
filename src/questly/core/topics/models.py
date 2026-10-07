"""Topic domain model.

This model deliberately has no FastAPI or database imports. Ids are ints
assigned by the repository, matching ADR 0006 and every other persisted table —
the UUIDs this slice used while it was in-memory are gone.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Topic:
    """A reusable subject classification for programming assignments.

    `id` is `None` only before the repository has persisted the Topic — see
    TopicRepository.create(). Anything a repository returns has a non-None id.
    """

    name: str
    description: str | None = None
    id: int | None = None
