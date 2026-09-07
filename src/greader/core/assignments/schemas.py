"""Assignment HTTP-contract placeholder.

Owner: Assignment teammate.
Define request and response schemas only after agreeing the Assignment use
cases. Keep transport validation separate from the domain model.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssignmentUpdate(BaseModel):
    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestCaseResponse(BaseModel):
    id: int
    assignment_id: int
    input_data: str
    expected_output: str
    is_hidden: bool
    order_index: int


class AssignmentResponse(BaseModel):
    id: int
    title: str
    problem_statement: str
    difficulty: str
    metadata: dict[str, Any]
    artifact_id: int | None = None
    test_cases: list[TestCaseResponse] = []
