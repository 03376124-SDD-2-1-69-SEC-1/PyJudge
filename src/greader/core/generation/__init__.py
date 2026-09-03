"""Generation slice: HTTP contract, client Protocol, and routes."""

from greader.core.generation.repository import GenerationClient
from greader.core.generation.schemas import (
    AssignmentDraft,
    Citation,
    GenerationFilters,
    GenerationRequest,
    GenerationResponse,
    TestCaseDraft,
)

__all__ = [
    "AssignmentDraft",
    "Citation",
    "GenerationClient",
    "GenerationFilters",
    "GenerationRequest",
    "GenerationResponse",
    "TestCaseDraft",
]
