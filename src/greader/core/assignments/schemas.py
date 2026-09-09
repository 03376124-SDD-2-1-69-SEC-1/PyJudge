"""Request and response schemas for the Assignment API."""

from typing import Literal

from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    """Fields required to create an Assignment."""

    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, object] = Field(default_factory=dict)


class AssignmentUpdate(AssignmentCreate):
    """Optional replacement fields for an existing Assignment."""

    title: str | None = Field(default=None, min_length=1)
    problem_statement: str | None = Field(default=None, min_length=1)
    difficulty: Literal["easy", "medium", "hard"] | None = None
    metadata: dict[str, object] | None = None


class AssignmentResponse(BaseModel):
    """Public representation of an Assignment returned by the API."""

    id: int
    title: str
    problem_statement: str
    difficulty: str
    metadata: dict[str, object] = Field(default_factory=dict)
    artifact_id: int | None = None


class TestCaseCreate(BaseModel):
    """Fields required to create a TestCase on an Assignment."""

    input_data: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)
    is_hidden: bool = False
    order_index: int = 0


class TestCaseUpdate(BaseModel):
    """Optional replacement fields for an existing TestCase."""

    input_data: str | None = Field(default=None, min_length=1)
    expected_output: str | None = Field(default=None, min_length=1)
    is_hidden: bool | None = None
    order_index: int | None = None


class TestCaseResponse(BaseModel):
    """Public representation of a TestCase returned by the API."""

    id: int
    assignment_id: int
    input_data: str
    expected_output: str
    is_hidden: bool
    order_index: int
