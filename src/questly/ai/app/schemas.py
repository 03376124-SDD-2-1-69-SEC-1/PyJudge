"""HTTP contracts for vector storage and similarity search."""

from pydantic import BaseModel, Field, StrictFloat, StrictInt

VectorValue = StrictInt | StrictFloat


class KnowledgeChunkCreate(BaseModel):
    """Chunk values accepted with a new knowledge source."""

    chunk_index: StrictInt
    page: StrictInt | None = None
    text: str
    token_count: StrictInt | None = None
    content_hash: str
    embedding_model: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    embedding: list[VectorValue] | None = None


class KnowledgeSourceCreate(BaseModel):
    """Request body for atomically creating one source and its chunks."""

    core_document_id: StrictInt
    r2_object_key: str
    content_hash: str
    status: str = "pending"
    embedding_model: str | None = None
    embedding_dim: StrictInt | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    chunks: list[KnowledgeChunkCreate]


class KnowledgeSourceResponse(BaseModel):
    """Created source representation without vector data."""

    id: int
    core_document_id: int
    r2_object_key: str
    content_hash: str
    status: str
    embedding_model: str | None
    embedding_dim: int | None
    metadata: dict[str, object]


class KnowledgeChunkResponse(BaseModel):
    """Created chunk representation without vector data."""

    id: int
    source_id: int
    chunk_index: int
    page: int | None
    text: str
    token_count: int | None
    content_hash: str
    embedding_model: str | None
    metadata: dict[str, object]


class KnowledgeSourceCreationResponse(BaseModel):
    """Source and chunks committed by one atomic operation."""

    source: KnowledgeSourceResponse
    chunks: list[KnowledgeChunkResponse]


class ChunkSearchRequest(BaseModel):
    """Vector and model used to search stored chunks."""

    embedding: list[VectorValue]
    embedding_model: str
    top_k: StrictInt


class ChunkSearchResultResponse(BaseModel):
    """One similarity result without vector data."""

    chunk_id: int
    source_id: int
    page: int | None
    text: str
    score: float


class ApplicationErrorDetail(BaseModel):
    """Stable detail shared by explicitly mapped application errors."""

    code: str
    message: str


class ApplicationErrorResponse(BaseModel):
    """Stable envelope shared by explicitly mapped application errors."""

    detail: ApplicationErrorDetail
