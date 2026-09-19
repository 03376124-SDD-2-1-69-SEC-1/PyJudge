"""Ports the upload use case needs: object storage and the document index.

`database/storage/r2.py` provides the R2 adapter for ObjectStorage and
`database/core/knowledge_document_repository.py` the SQL adapter for the
repository. Nothing in `core/` may import either; only `main.py` wires them in.
"""

from typing import Protocol

from greader.core.uploads.models import KnowledgeDocument, StoredObject


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
