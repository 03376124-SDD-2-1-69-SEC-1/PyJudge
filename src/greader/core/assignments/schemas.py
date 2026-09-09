"""Request and response schemas for the Assignment API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("metadata", mode="before")
    def ensure_metadata_dict(cls, v: object) -> dict[str, object]:
        """Normalize invalid or absent metadata values to an empty mapping."""
        return v if isinstance(v, dict) else {}
