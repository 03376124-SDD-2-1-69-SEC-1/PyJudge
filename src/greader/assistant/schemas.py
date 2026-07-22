"""Strict structured-output schemas for AI-generated assignment content."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from greader.assignments.models import Difficulty, TestCaseCategory


class GenerationMode(StrEnum):
    """Supported assignment-generation modes."""

    FULL_ASSIGNMENT = "full_assignment"
    TEST_CASES = "test_cases"
    EDGE_CASES = "edge_cases"


class GeneratedExample(BaseModel):
    """A generated sample input/output pair."""

    model_config = ConfigDict(extra="forbid")

    input_data: str
    expected_output: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class GeneratedTestCase(BaseModel):
    """A generated candidate test case."""

    model_config = ConfigDict(extra="forbid")

    input_data: str
    expected_output: str = Field(min_length=1)
    category: TestCaseCategory
    explanation: str = Field(min_length=1)


class FullAssignmentDraft(BaseModel):
    """A complete programming-assignment draft returned by a provider."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=120)
    problem_statement: str = Field(min_length=20, max_length=10_000)
    input_format: str = Field(min_length=3, max_length=3_000)
    output_format: str = Field(min_length=3, max_length=3_000)
    constraints: list[str] = Field(min_length=1, max_length=20)
    difficulty: Difficulty
    learning_objectives: list[str] = Field(min_length=1, max_length=10)
    reference_solution: str = Field(max_length=20_000)
    examples: list[GeneratedExample] = Field(min_length=1, max_length=10)
    test_cases: list[GeneratedTestCase] = Field(min_length=1, max_length=30)
    ambiguity_notes: list[str] = Field(default_factory=list, max_length=15)

    @field_validator("reference_solution")
    @classmethod
    def _reference_solution_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reference_solution must not be empty")
        return value


class TestCaseDraftSet(BaseModel):
    """A generated set of candidate test cases for an existing assignment."""

    model_config = ConfigDict(extra="forbid")

    test_cases: list[GeneratedTestCase] = Field(min_length=1, max_length=30)
    coverage_notes: list[str] = Field(default_factory=list, max_length=15)
    ambiguity_notes: list[str] = Field(default_factory=list, max_length=15)


DraftPayload = FullAssignmentDraft | TestCaseDraftSet


class GenerationResult(BaseModel):
    """Application-facing provider result."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    summary: str = Field(min_length=1)
    mode: GenerationMode
    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    payload: DraftPayload
