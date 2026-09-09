from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    problem_statement: str | None = Field(default=None, min_length=1)
    difficulty: Literal["easy", "medium", "hard"] | None = None
    metadata: dict[str, Any] | None = None


class AssignmentResponse(BaseModel):
    id: int
    title: str
    problem_statement: str
    difficulty: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    artifact_id: int | None = None

    @field_validator("metadata", mode="before")
    def ensure_metadata_dict(cls, v: Any) -> dict[str, Any]:
        return v if isinstance(v, dict) else {}