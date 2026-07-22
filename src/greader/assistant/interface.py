"""Application-facing generation request and provider protocol."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from greader.assignments.models import Assignment
from greader.assistant.schemas import GenerationMode, GenerationResult


class GenerationRequest(BaseModel):
    """Validated instructor generation request."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=4_000)
    mode: GenerationMode
    assignment_id: str | None = None

    @field_validator("prompt", mode="before")
    @classmethod
    def _trim_prompt(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class AssignmentGenerator(Protocol):
    """Provider interface for assignment generation."""

    provider_name: str
    model_name: str

    def generate(
        self,
        request: GenerationRequest,
        assignment: Assignment | None,
    ) -> GenerationResult:
        """Generate structured assignment content."""
        ...
