"""Generation slice: HTTP contract, client Protocol, and routes."""

from greader.core.generation.ports import GenerationClient
from greader.core.generation.schemas import (
    GenerationFilters,
    GenerationRequest,
    GenerationResponse,
)

__all__ = [
    "GenerationClient",
    "GenerationFilters",
    "GenerationRequest",
    "GenerationResponse",
]
