"""Assignment HTTP-contract schemas.

Keep transport validation separate from the domain model.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, object] = Field(default_factory=dict)


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    problem_statement: str | None = Field(default=None, min_length=1)
    difficulty: Literal["easy", "medium", "hard"] | None = None
    metadata: dict[str, object] | None = None


class AssignmentResponse(BaseModel):
    id: int
    title: str
    problem_statement: str
    difficulty: str
    metadata: dict[str, object] = Field(default_factory=dict)
    artifact_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
