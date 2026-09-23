"""Shared HTTP contract for assignment generation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from greader.core.assignments.models import Difficulty, Language, TestCaseKind
from greader.core.generation.models import ReviewStatus


class ContractModel(BaseModel):
    """Base model that rejects fields outside the shared contract."""

    model_config = ConfigDict(extra="forbid")


class GenerationFilters(ContractModel):
    """Optional metadata filters applied while retrieving source material."""

    topic: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None


class GenerationRequest(ContractModel):
    """What Core asks the AI client for."""

    prompt: str
    filters: GenerationFilters | None = None
    document_ids: list[int] = []


class TestCaseDraft(ContractModel):
    """Generated input and expected output for an Assignment."""

    input_data: str
    expected_output: str
    is_hidden: bool = False
    order_index: int = 0


class AssignmentDraft(ContractModel):
    """Generated Assignment content awaiting instructor review."""

    title: str
    statement: str
    test_cases: list[TestCaseDraft]


class Citation(ContractModel):
    """Source excerpt supporting generated Assignment content."""

    chunk_id: int
    source_id: int
    page: int | None
    score: float
    text_snapshot: str


class GenerationResponse(ContractModel):
    """Draft and supporting citations a GenerationClient returns.

    This is the wire shape between Core and the AI client -- it carries no id
    because nothing has been persisted yet at that point. The persisted
    artifact returned by the HTTP endpoints is `GenerationArtifactResponse`.
    """

    draft: AssignmentDraft
    citations: list[Citation]


class GenerationArtifactResponse(ContractModel):
    """Persisted generation artifact returned by the generation endpoints."""

    id: int
    draft: AssignmentDraft
    citations: list[Citation]
    review_status: ReviewStatus


# ---- ADR-0007 Drafts API ---------------------------------------------------


class DraftCreate(BaseModel):
    """T-03: what to generate and from which Documents."""

    prompt: str = Field(min_length=1, max_length=4000)
    difficulty: Difficulty = Difficulty.MEDIUM
    topic_id: int | None = None
    document_ids: list[int] = Field(default_factory=list)


class DraftTestCase(BaseModel):
    input_data: str
    expected_output: str
    kind: TestCaseKind = TestCaseKind.SAMPLE
    note: str = Field(default="", max_length=120)


class DraftPatch(BaseModel):
    """Save one T-04 step; fields left out keep their value."""

    title: str | None = Field(default=None, max_length=200)
    problem_statement: str | None = None
    difficulty: Difficulty | None = None
    topic_id: int | None = None
    test_cases: list[DraftTestCase] | None = None
    time_limit_ms: int | None = Field(default=None, gt=0, le=10_000)
    language: Language | None = None
    show_hidden_names: bool | None = None
    deadline: datetime | None = None
    max_score: int | None = Field(default=None, gt=0)
    allow_late: bool | None = None
    allow_resubmission: bool | None = None
    classroom_ids: list[int] | None = None


class RegenerateRequest(BaseModel):
    part: str = Field(pattern="^(title|description)$")


class PublishRequest(BaseModel):
    classroom_ids: list[int] | None = None


class DraftCitation(BaseModel):
    source_id: int
    page: int | None
    text_snapshot: str


class DraftResponse(BaseModel):
    id: int
    classroom_id: int
    status: str
    prompt: str
    generated_at: datetime
    title: str
    problem_statement: str
    difficulty: Difficulty
    topic_id: int | None
    test_cases: list[DraftTestCase]
    time_limit_ms: int
    language: Language
    show_hidden_names: bool
    deadline: datetime | None
    max_score: int
    allow_late: bool
    allow_resubmission: bool
    classroom_ids: list[int]
    document_ids: list[int]
    citations: list[DraftCitation]
    assignment_id: int | None


class PublishResponse(BaseModel):
    assignment_id: int
    posting_ids: list[int]
