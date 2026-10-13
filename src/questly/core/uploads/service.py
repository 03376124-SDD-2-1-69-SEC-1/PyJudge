"""Upload use cases, independent from HTTP and storage technology."""

from __future__ import annotations

import logging
from dataclasses import replace
from hashlib import sha256
from pathlib import PurePosixPath
from uuid import uuid4

from questly.core.auth.models import Actor, PermissionDeniedError, Role
from questly.core.uploads.models import (
    DocumentStatus,
    KnowledgeDocument,
    StoredUpload,
)
from questly.core.uploads.ports import (
    DocumentIngestor,
    KnowledgeDocumentRepository,
    ObjectStorage,
)

KEY_PREFIX = "uploads/"

logger = logging.getLogger(__name__)


class UploadTooLargeError(Exception):
    """Raised when an uploaded file exceeds the configured size limit."""


class EmptyUploadError(Exception):
    """Raised when an upload carries no bytes or no usable filename."""


class KnowledgeDocumentNotFoundError(Exception):
    """Raised when a requested knowledge document does not exist."""


class UploadService:
    """Store an uploaded file, index it as a knowledge document, ingest it."""

    def __init__(
        self,
        storage: ObjectStorage,
        repository: KnowledgeDocumentRepository,
        ingestor: DocumentIngestor,
        *,
        max_upload_size_bytes: int,
    ) -> None:
        """Initialize the service with its storage, repository and ingestor seams."""
        self._storage = storage
        self._repository = repository
        self._ingestor = ingestor
        self.max_upload_size_bytes = max_upload_size_bytes

    def store(self, actor: Actor, *, filename: str, data: bytes) -> StoredUpload:
        """Upload the bytes and return the document row that indexes them.

        Uploading the same content twice is idempotent: `content_hash` exists to
        keep one file from being ingested twice, so an identical upload returns
        the document already on record, `created=False`, instead of writing a
        second object. That includes another Instructor's document.
        """
        if actor.role is not Role.INSTRUCTOR:
            raise PermissionDeniedError
        name = _safe_filename(filename)
        if not data:
            raise EmptyUploadError
        if len(data) > self.max_upload_size_bytes:
            raise UploadTooLargeError

        content_hash = sha256(data).hexdigest()
        existing = self._repository.get_by_content_hash(content_hash)
        if existing is not None:
            return StoredUpload(existing, created=False)

        stored = self._storage.put(f"{KEY_PREFIX}{uuid4().hex}-{name}", data)
        document = self._repository.create(
            KnowledgeDocument(
                filename=name,
                object_key=stored.key,
                content_hash=content_hash,
                status=DocumentStatus.UPLOADED,
                uploaded_by=actor.user_id,
            )
        )
        return StoredUpload(document, created=True)

    def ingest(self, document_id: int, data: bytes) -> None:
        """Index an uploaded document and move it to `ready`, or to `failed`.

        Runs in a background task after the upload was answered, so nothing here
        may raise to a caller: any ingestion error is logged and recorded as the
        document's status. `data` is the upload already in memory, so the bytes
        are not fetched from storage again.
        """
        document = self.get(document_id)
        self._repository.update(replace(document, status=DocumentStatus.INGESTING))
        try:
            outcome = self._ingestor.ingest(document, data)
            self._repository.update(
                replace(
                    document,
                    status=DocumentStatus.READY,
                    page_count=outcome.page_count,
                )
            )
        except Exception:
            logger.exception("Ingesting knowledge document %s failed", document_id)
            self._repository.update(replace(document, status=DocumentStatus.FAILED))

    def get(self, document_id: int) -> KnowledgeDocument:
        """Return one document or raise when it does not exist."""
        document = self._repository.get(document_id)
        if document is None:
            raise KnowledgeDocumentNotFoundError
        return document


def _safe_filename(filename: str) -> str:
    """Return the bare filename, refusing anything that could escape the prefix.

    A client controls this value, and it ends up in an object key. Keeping only
    the last path segment stops `../` and absolute paths from moving the object
    out of `uploads/`.
    """
    name = PurePosixPath(filename.strip().replace("\\", "/")).name
    if not name or name in {".", ".."}:
        raise EmptyUploadError
    return name
