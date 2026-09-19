"""Upload use cases, independent from HTTP and storage technology."""

from __future__ import annotations

from hashlib import sha256
from pathlib import PurePosixPath
from uuid import uuid4

from greader.core.uploads.models import DocumentStatus, KnowledgeDocument
from greader.core.uploads.ports import KnowledgeDocumentRepository, ObjectStorage

KEY_PREFIX = "uploads/"


class UploadTooLargeError(Exception):
    """Raised when an uploaded file exceeds the configured size limit."""


class EmptyUploadError(Exception):
    """Raised when an upload carries no bytes or no usable filename."""


class KnowledgeDocumentNotFoundError(Exception):
    """Raised when a requested knowledge document does not exist."""


class UploadService:
    """Store an uploaded file and index it as a knowledge document."""

    def __init__(
        self,
        storage: ObjectStorage,
        repository: KnowledgeDocumentRepository,
        *,
        max_upload_size_bytes: int,
    ) -> None:
        """Initialize the service with its storage and repository seams."""
        self._storage = storage
        self._repository = repository
        self.max_upload_size_bytes = max_upload_size_bytes

    def store(self, *, filename: str, data: bytes) -> KnowledgeDocument:
        """Upload the bytes and return the document row that indexes them.

        Uploading the same content twice is idempotent: `content_hash` exists to
        keep one file from being ingested twice, so an identical upload returns
        the document already on record instead of writing a second object.
        """
        name = _safe_filename(filename)
        if not data:
            raise EmptyUploadError
        if len(data) > self.max_upload_size_bytes:
            raise UploadTooLargeError

        content_hash = sha256(data).hexdigest()
        existing = self._repository.get_by_content_hash(content_hash)
        if existing is not None:
            return existing

        stored = self._storage.put(f"{KEY_PREFIX}{uuid4().hex}-{name}", data)
        return self._repository.create(
            KnowledgeDocument(
                filename=name,
                object_key=stored.key,
                content_hash=content_hash,
                status=DocumentStatus.UPLOADED,
            )
        )

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
