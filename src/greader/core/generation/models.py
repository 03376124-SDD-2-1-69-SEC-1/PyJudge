"""Domain representation of a generated Assignment draft and its citations."""

from dataclasses import dataclass, field
from enum import StrEnum


class ReviewStatus(StrEnum):
    """Where a generation artifact stands in instructor review.

    The same three values the `core.generation_artifacts` CHECK constraint
    allows, declared here so an invalid status fails in the domain instead of
    at the database.
    """

    PENDING = "pending"
    APPLIED = "applied"
    DISCARDED = "discarded"


@dataclass(frozen=True, slots=True)
class TestCaseDraft:
    """A single generated input/output pair awaiting instructor review."""

    input_data: str
    expected_output: str
    is_hidden: bool = False
    order_index: int = 0


@dataclass(frozen=True, slots=True)
class AssignmentDraft:
    """Generated Assignment content awaiting instructor review."""

    title: str
    statement: str
    test_cases: list[TestCaseDraft] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Citation:
    """Source excerpt supporting generated Assignment content.

    `chunk_id`/`source_id` point at rows in the `rag` schema. There is no FK
    between `core` and `rag` -- the two sync over HTTP only -- so these are
    business facts a citation carries about itself, not columns that exist
    only to satisfy a table. Allowlisted in
    `test_domain_models_hold_no_table_only_fields`.
    """

    chunk_id: int
    source_id: int
    page: int | None
    score: float
    text_snapshot: str


@dataclass(frozen=True, slots=True)
class GenerationArtifact:
    """A generated draft, its citations, and its review state.

    `id` is `None` only before the repository has persisted the artifact --
    see GenerationRepository.create_artifact(). Anything a repository returns
    has a non-None id.
    """

    draft: AssignmentDraft
    citations: list[Citation]
    id: int | None = None
    review_status: ReviewStatus = ReviewStatus.PENDING
