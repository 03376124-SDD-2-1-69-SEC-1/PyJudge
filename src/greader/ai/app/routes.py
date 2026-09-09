"""FastAPI adapter for vector storage and similarity search."""

from fastapi import APIRouter, HTTPException, Request, status

from greader.ai.app.models import (
    ChunkSearchResult,
    KnowledgeChunk,
    KnowledgeSource,
    NewKnowledgeChunk,
    NewKnowledgeSource,
)
from greader.ai.app.repository import (
    DuplicateChunkError,
    DuplicateSourceError,
    VectorRepositoryUnavailableError,
)
from greader.ai.app.schemas import (
    ApplicationErrorResponse,
    ChunkSearchRequest,
    ChunkSearchResultResponse,
    KnowledgeChunkCreate,
    KnowledgeChunkResponse,
    KnowledgeSourceCreate,
    KnowledgeSourceCreationResponse,
    KnowledgeSourceResponse,
)
from greader.ai.app.service import VectorService, VectorValidationError

router = APIRouter(prefix="/api/v1", tags=["vector-storage"])

_APPLICATION_ERROR_RESPONSES = {
    409: {"model": ApplicationErrorResponse},
    422: {"model": ApplicationErrorResponse},
    503: {"model": ApplicationErrorResponse},
}


def _service(request: Request) -> VectorService:
    return request.app.state.vector_service


def _raise_application_error(*, status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _new_chunk(payload: KnowledgeChunkCreate) -> NewKnowledgeChunk:
    return NewKnowledgeChunk(
        chunk_index=payload.chunk_index,
        page=payload.page,
        text=payload.text,
        token_count=payload.token_count,
        content_hash=payload.content_hash,
        embedding_model=payload.embedding_model,
        metadata=payload.metadata,
        embedding=tuple(payload.embedding) if payload.embedding is not None else None,
    )


def _source_response(source: KnowledgeSource) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=source.id,
        core_document_id=source.core_document_id,
        r2_object_key=source.r2_object_key,
        content_hash=source.content_hash,
        status=source.status,
        embedding_model=source.embedding_model,
        embedding_dim=source.embedding_dim,
        metadata=dict(source.metadata),
    )


def _chunk_response(chunk: KnowledgeChunk) -> KnowledgeChunkResponse:
    return KnowledgeChunkResponse(
        id=chunk.id,
        source_id=chunk.source_id,
        chunk_index=chunk.chunk_index,
        page=chunk.page,
        text=chunk.text,
        token_count=chunk.token_count,
        content_hash=chunk.content_hash,
        embedding_model=chunk.embedding_model,
        metadata=dict(chunk.metadata),
    )


def _search_response(result: ChunkSearchResult) -> ChunkSearchResultResponse:
    return ChunkSearchResultResponse(
        chunk_id=result.chunk_id,
        source_id=result.source_id,
        page=result.page,
        text=result.text,
        score=result.score,
    )


@router.post(
    "/knowledge-sources",
    response_model=KnowledgeSourceCreationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_APPLICATION_ERROR_RESPONSES,
)
def create_knowledge_source(
    request: Request, payload: KnowledgeSourceCreate
) -> KnowledgeSourceCreationResponse:
    """Atomically create one knowledge source and its chunks."""
    source = NewKnowledgeSource(
        core_document_id=payload.core_document_id,
        r2_object_key=payload.r2_object_key,
        content_hash=payload.content_hash,
        embedding_model=payload.embedding_model,
        embedding_dim=payload.embedding_dim,
        metadata=payload.metadata,
    )
    chunks = tuple(_new_chunk(chunk) for chunk in payload.chunks)

    try:
        result = _service(request).create_source_with_chunks(source, chunks)
    except VectorValidationError as exc:
        _raise_application_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="vector_validation_error",
            message=str(exc),
        )
    except DuplicateSourceError:
        _raise_application_error(
            status_code=status.HTTP_409_CONFLICT,
            code="duplicate_knowledge_source",
            message="knowledge source already exists",
        )
    except DuplicateChunkError:
        _raise_application_error(
            status_code=status.HTTP_409_CONFLICT,
            code="duplicate_knowledge_chunk",
            message="knowledge source contains duplicate chunks",
        )
    except VectorRepositoryUnavailableError:
        _raise_application_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="vector_repository_unavailable",
            message="vector repository is unavailable",
        )

    return KnowledgeSourceCreationResponse(
        source=_source_response(result.source),
        chunks=[_chunk_response(chunk) for chunk in result.chunks],
    )


@router.post(
    "/knowledge-chunks/search",
    response_model=list[ChunkSearchResultResponse],
    responses={
        422: {"model": ApplicationErrorResponse},
        503: {"model": ApplicationErrorResponse},
    },
)
def search_knowledge_chunks(
    request: Request, payload: ChunkSearchRequest
) -> list[ChunkSearchResultResponse]:
    """Search chunks for one embedding model using cosine similarity."""
    try:
        results = _service(request).search(
            tuple(payload.embedding),
            embedding_model=payload.embedding_model,
            top_k=payload.top_k,
        )
    except VectorValidationError as exc:
        _raise_application_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="vector_validation_error",
            message=str(exc),
        )
    except VectorRepositoryUnavailableError:
        _raise_application_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="vector_repository_unavailable",
            message="vector repository is unavailable",
        )

    return [_search_response(result) for result in results]
