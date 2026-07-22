"""Domain models for persisted generation artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from greader.assistant.schemas import DraftPayload, GenerationMode


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
    is_applied: bool = False
    created_at: datetime | None = None
    applied_at: datetime | None = None
