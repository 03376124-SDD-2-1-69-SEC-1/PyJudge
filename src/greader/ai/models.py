"""Domain models for persisted generation artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from greader.ai.schemas import DraftPayload, GenerationMode


class ArtifactStatus(StrEnum):
    """Instructor review state for a generated artifact."""

    DRAFT = "draft"
    APPLIED = "applied"
    DISCARDED = "discarded"


@dataclass
class GenerationArtifact:
    """Validated persisted provider output."""

    id: str
    generation_request_id: str
    mode: GenerationMode
    provider: str
    model_name: str
    summary: str
    payload: DraftPayload
    assignment_id: str | None = None
    review_status: ArtifactStatus = ArtifactStatus.DRAFT
    created_at: datetime | None = None
    reviewed_at: datetime | None = None
