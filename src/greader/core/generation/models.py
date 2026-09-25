"""Domain representation of a generated Assignment draft and its citations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from greader.core.assignments.models import AssignmentContent, TestCaseKind


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
    between `core` and `rag` -- they never reference each other by key -- so these are
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


# ---- ADR-0007 §4: Drafts reviewed in the T-04 stepper -----------------------


class DraftStatus(StrEnum):
    """A Draft leaves the Drafts list once it is published."""

    REVIEWING = "reviewing"
    PUBLISHED = "published"


class DraftPart(StrEnum):
    """What T-03a "Regenerate this part" can redo."""

    TITLE = "title"
    DESCRIPTION = "description"


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    """A Document an Instructor may let generation read (T-03 picker)."""

    id: int
    filename: str
    pages: int


@dataclass(frozen=True, slots=True)
class DraftSettings:
    """T-04 step 3's schedule and policy (the judging half lives on the content).

    `deadline` stays `None` until the Instructor picks one.
    """

    deadline: datetime | None = None
    max_score: int = 10
    allow_late: bool = False
    allow_resubmission: bool = True


@dataclass(frozen=True, slots=True)
class Draft:
    """A generated Assignment under review, owned by the Instructor who asked.

    `content` is what steps 1-2 edit, `settings` step 3, `classroom_ids`
    step 4 (the Classroom it was generated in is pre-chosen). After
    publishing, `assignment_id` points at the new Assignment.
    """

    classroom_id: int
    requested_by: int
    prompt: str
    content: AssignmentContent
    generated_at: datetime
    citations: list[Citation] = field(default_factory=list)
    document_ids: list[int] = field(default_factory=list)
    settings: DraftSettings = field(default_factory=DraftSettings)
    classroom_ids: list[int] = field(default_factory=list)
    status: DraftStatus = DraftStatus.REVIEWING
    assignment_id: int | None = None
    id: int | None = None

    @property
    def sample_count(self) -> int:
        return sum(
            1 for tc in self.content.test_cases if tc.kind is TestCaseKind.SAMPLE
        )


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    """T-03 "Uses 1 of your 20 daily generations" / A-01 "18 / 20 today"."""

    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)
