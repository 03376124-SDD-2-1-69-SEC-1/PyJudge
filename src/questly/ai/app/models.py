"""Domain contracts for vector storage and similarity search.

The existing ``rag.knowledge_sources`` table requires ``core_document_id``,
``r2_object_key``, ``content_hash``, and ``status``. New sources default to the
allowed ``pending`` status. Embedding model, dimension, and metadata are optional.

The existing ``rag.knowledge_chunks`` table requires its parent source,
``chunk_index``, ``text``, and ``content_hash``. The atomic repository operation
assigns the parent source ID. Page, token count, embedding model, metadata, and
embedding are optional. A supplied embedding contains exactly 768 values.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

EMBEDDING_DIMENSION = 768
Embedding = tuple[float, ...]
Metadata = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class NewKnowledgeSource:
    """Values accepted before a knowledge source has a database ID."""

    core_document_id: int
    r2_object_key: str
    content_hash: str
    status: str = "pending"
    embedding_model: str | None = None
    embedding_dim: int | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NewKnowledgeChunk:
    """Values accepted before a chunk and its parent source have database IDs."""

    chunk_index: int
    text: str
    content_hash: str
    page: int | None = None
    token_count: int | None = None
    embedding_model: str | None = None
    metadata: Metadata = field(default_factory=dict)
    embedding: Embedding | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    """A persisted knowledge source with a database-assigned integer ID."""

    id: int
    core_document_id: int
    r2_object_key: str
    content_hash: str
    status: str
    embedding_model: str | None
    embedding_dim: int | None
    metadata: Metadata


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """A persisted knowledge chunk with database-assigned integer IDs."""

    id: int
    source_id: int
    chunk_index: int
    page: int | None
    text: str
    token_count: int | None
    content_hash: str
    embedding_model: str | None
    metadata: Metadata
    embedding: Embedding | None


@dataclass(frozen=True, slots=True)
class SourceCreationResult:
    """The source and chunks persisted by one atomic repository operation."""

    source: KnowledgeSource
    chunks: tuple[KnowledgeChunk, ...]


@dataclass(frozen=True, slots=True)
class ChunkSearchResult:
    """A vector match where score is similarity, not confidence or probability."""

    chunk_id: int
    source_id: int
    page: int | None
    text: str
    score: float
