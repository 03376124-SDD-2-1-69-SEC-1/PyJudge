"""FastAPI adapter for the knowledge document upload API."""

from typing import NoReturn

from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from greader.core.uploads.models import KnowledgeDocument
from greader.core.uploads.schemas import KnowledgeDocumentResponse
from greader.core.uploads.service import (
    EmptyUploadError,
    KnowledgeDocumentNotFoundError,
    UploadService,
    UploadTooLargeError,
)

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])


def _service(request: Request) -> UploadService:
    return request.app.state.upload_service


def _response(document: KnowledgeDocument) -> KnowledgeDocumentResponse:
    return KnowledgeDocumentResponse(
        id=document.id,
        filename=document.filename,
        object_key=document.object_key,
        content_hash=document.content_hash,
        status=document.status,
    )


def _raise_not_found() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "knowledge_document_not_found",
            "message": "Knowledge document not found",
        },
    )


def _raise_too_large() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail={"code": "upload_too_large", "message": "File exceeds size limit"},
    )


def _raise_empty_upload() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "empty_upload",
            "message": "Upload needs a filename and at least one byte",
        },
    )


@router.post(
    "",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_upload(request: Request, file: UploadFile) -> KnowledgeDocumentResponse:
    """Store an uploaded file and index it as a knowledge document."""
    service = _service(request)
    filename = file.filename
    if filename is None:
        _raise_empty_upload()

    # One byte past the limit is enough to know the file is too big, so an
    # oversized upload is never held in memory in full.
    data = file.file.read(service.max_upload_size_bytes + 1)
    try:
        return _response(service.store(filename=filename, data=data))
    except UploadTooLargeError:
        _raise_too_large()
    except EmptyUploadError:
        _raise_empty_upload()


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
def get_upload(document_id: int, request: Request) -> KnowledgeDocumentResponse:
    """Get one knowledge document, which is how a citation resolves a filename."""
    try:
        return _response(_service(request).get(document_id))
    except KnowledgeDocumentNotFoundError:
        _raise_not_found()
