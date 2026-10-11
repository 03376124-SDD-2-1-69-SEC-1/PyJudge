"""Repository operation required by filtered retrieval."""

from typing import Protocol

from questly.ai.app.models import ChunkSearchResult, Embedding
from questly.ai.retrieval.models import RetrievalFilters


class FilteredVectorRepository(Protocol):
    """Rank ready-source chunks after filtering in the vector store."""

    def search_filtered(
        self,
        embedding: Embedding,
        *,
        embedding_model: str,
        limit: int,
        filters: RetrievalFilters,
    ) -> list[ChunkSearchResult]:
        """Return score-descending matches, breaking ties by chunk ID."""
        ...
