"""Repository port for atomic vector storage and similarity search.

Adapters must translate storage failures into ``VectorRepositoryError`` types;
SQLAlchemy, driver, and provider exceptions must not cross this boundary.

``core_document_id`` is UNIQUE for sources. ``(source_id, content_hash)`` is
UNIQUE for chunks. An adapter raises ``DuplicateSourceError`` or
``DuplicateChunkError`` for those conflicts and rolls back the source and every
chunk. No partial source or chunk data may remain after any creation failure.
"""

from math import sqrt
from typing import Protocol

from greader.ai.app.models import (
    ChunkSearchResult,
    Embedding,
    KnowledgeChunk,
    KnowledgeSource,
    NewKnowledgeChunk,
    NewKnowledgeSource,
    SourceCreationResult,
)


class VectorRepositoryError(Exception):
    """Base error for all adapter failures exposed through this port."""


class DuplicateSourceError(VectorRepositoryError):
    """Raised when a source repeats the UNIQUE ``core_document_id`` value."""


class DuplicateChunkError(VectorRepositoryError):
    """Raised when chunks repeat ``content_hash`` under the same source."""


class VectorRepository(Protocol):
    """Persistence operations required by vector-storage use cases."""

    def create_source_with_chunks(
        self,
        source: NewKnowledgeSource,
        chunks: tuple[NewKnowledgeChunk, ...],
    ) -> SourceCreationResult:
        """Create one source and all chunks in one transaction.

        The adapter assigns integer IDs. Any failure rolls back the complete
        operation. Duplicate errors follow the module-level contract.
        """
        ...

    def search(
        self,
        embedding: Embedding,
        *,
        embedding_model: str,
        limit: int,
    ) -> list[ChunkSearchResult]:
        """Return matches for exactly one embedding model.

        Score equals ``1 - cosine distance`` and measures vector similarity,
        not confidence or probability. Results use descending score, then
        ascending ``chunk_id`` for ties. Return an empty list when nothing
        matches the requested embedding model.
        """
        ...


class InMemoryVectorRepository:
    """Process-local adapter with database-like IDs and uniqueness rules."""

    def __init__(self) -> None:
        self._sources: dict[int, KnowledgeSource] = {}
        self._source_ids_by_core_document: dict[int, int] = {}
        self._chunks: dict[int, KnowledgeChunk] = {}
        self._next_source_id = 1
        self._next_chunk_id = 1

    def create_source_with_chunks(
        self,
        source: NewKnowledgeSource,
        chunks: tuple[NewKnowledgeChunk, ...],
    ) -> SourceCreationResult:
        if source.core_document_id in self._source_ids_by_core_document:
            raise DuplicateSourceError

        content_hashes = [chunk.content_hash for chunk in chunks]
        if len(content_hashes) != len(set(content_hashes)):
            raise DuplicateChunkError

        source_id = self._next_source_id
        stored_source = KnowledgeSource(
            id=source_id,
            core_document_id=source.core_document_id,
            r2_object_key=source.r2_object_key,
            content_hash=source.content_hash,
            status=source.status,
            embedding_model=source.embedding_model,
            embedding_dim=source.embedding_dim,
            metadata=dict(source.metadata),
        )
        stored_chunks = tuple(
            KnowledgeChunk(
                id=self._next_chunk_id + offset,
                source_id=source_id,
                chunk_index=chunk.chunk_index,
                page=chunk.page,
                text=chunk.text,
                token_count=chunk.token_count,
                content_hash=chunk.content_hash,
                embedding_model=chunk.embedding_model,
                metadata=dict(chunk.metadata),
                embedding=chunk.embedding,
            )
            for offset, chunk in enumerate(chunks)
        )

        self._sources[source_id] = stored_source
        self._source_ids_by_core_document[source.core_document_id] = source_id
        self._chunks.update({chunk.id: chunk for chunk in stored_chunks})
        self._next_source_id += 1
        self._next_chunk_id += len(stored_chunks)
        return SourceCreationResult(source=stored_source, chunks=stored_chunks)

    def search(
        self,
        embedding: Embedding,
        *,
        embedding_model: str,
        limit: int,
    ) -> list[ChunkSearchResult]:
        matches = [
            ChunkSearchResult(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                page=chunk.page,
                text=chunk.text,
                score=_cosine_similarity(embedding, chunk.embedding),
            )
            for chunk in self._chunks.values()
            if chunk.embedding is not None and chunk.embedding_model == embedding_model
        ]
        matches.sort(key=lambda match: (-match.score, match.chunk_id))
        return matches[:limit]


def _cosine_similarity(left: Embedding, right: Embedding) -> float:
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    return dot_product / (left_norm * right_norm)
