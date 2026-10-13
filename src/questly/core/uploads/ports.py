"""Ports the upload use case needs: object storage, the document index, ingestion.

`database/storage/r2.py` provides the R2 adapter for ObjectStorage and
`database/core/knowledge_document_repository.py` the SQL adapter for the
repository; `ai/ingestor.py` provides the DocumentIngestor. Nothing in `core/`
may import any of them; only `main.py` wires them in.
"""

from typing import Protocol

from questly.core.uploads.models import (
    IngestionOutcome,
    KnowledgeDocument,
    StoredObject,
)


class ObjectStorage(Protocol):
    """Somewhere to put the bytes of an uploaded file."""

    def put(self, key: str, data: bytes) -> StoredObject:
        """Store `data` under `key` and report where it landed."""
        ...


class KnowledgeDocumentRepository(Protocol):
    """Persistence operations required by UploadService.

    `create` is the only operation allowed to assign an id: it takes a
    KnowledgeDocument whose `id` is `None` and returns one whose `id` is a real
    int. Callers must always use the returned object, never the one they passed.
    """

    def create(self, document: KnowledgeDocument) -> KnowledgeDocument: ...

    def get(self, document_id: int) -> KnowledgeDocument | None: ...

    def get_by_content_hash(self, content_hash: str) -> KnowledgeDocument | None: ...

    def update(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Replace the stored document; `KeyError` when its id is unknown."""
        ...


class DocumentIngestionError(Exception):
    """The document cannot be turned into searchable chunks."""


class DocumentIngestor(Protocol):
    """Turns a stored document's bytes into chunks generation can retrieve."""

    def ingest(self, document: KnowledgeDocument, data: bytes) -> IngestionOutcome:
        """Index `data` for `document`, or raise DocumentIngestionError."""
        ...
