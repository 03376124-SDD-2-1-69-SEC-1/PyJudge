"""Shared HTTP contract for assignment generation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Base model that rejects fields outside the shared contract."""

    model_config = ConfigDict(extra="forbid")


class GenerationFilters(ContractModel):
    """Optional metadata filters applied while retrieving source material."""

    topic: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None


class GenerationRequest(ContractModel):
    """Input accepted by the generation endpoint."""

    prompt: str
    filters: GenerationFilters | None = None


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
    """Draft and supporting citations returned by the generation endpoint."""

    draft: AssignmentDraft
    citations: list[Citation]
