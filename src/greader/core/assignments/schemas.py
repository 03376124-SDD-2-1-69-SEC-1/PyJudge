"""Assignment HTTP-contract placeholder.

Owner: Assignment teammate.
Define request and response schemas only after agreeing the Assignment use
cases. Keep transport validation separate from the domain model.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# === Test Case Schemas ===
class TestCaseBase(BaseModel):
    input_data: str
    expected_output: str
    is_hidden: bool = False
    weight: float = Field(default=1.0, ge=0.0)


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
    input_data: str | None = None
    expected_output: str | None = None
    is_hidden: bool | None = None
    weight: float | None = Field(default=None, ge=0.0)


class TestCaseResponse(TestCaseBase):
    id: int
    assignment_id: int

    model_config = ConfigDict(from_attributes=True)


# === Assignment Schemas ===
class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssignmentUpdate(BaseModel):
    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, Any] = Field(default=None)


class AssignmentResponse(BaseModel):
    id: int
    title: str
    problem_statement: str
    difficulty: str
    metadata: dict[str, Any]
    artifact_id: int | None = None
    test_cases: list[TestCaseResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
