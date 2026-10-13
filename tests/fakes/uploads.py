"""In-memory ObjectStorage, KnowledgeDocumentRepository and DocumentIngestor."""

from __future__ import annotations

from dataclasses import replace

from questly.core.uploads.models import (
    IngestionOutcome,
    KnowledgeDocument,
    StoredObject,
)
from questly.core.uploads.ports import DocumentIngestionError

FAKE_BUCKET = "fake-bucket"


class FakeObjectStorage:
    """Keep uploaded bytes in a dict instead of calling R2."""

    def __init__(self, bucket: str = FAKE_BUCKET) -> None:
        """Initialize empty storage for the given bucket name."""
        self.bucket = bucket
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> StoredObject:
        """Store `data` under `key` and report where it landed."""
        self.objects[key] = data
        return StoredObject(bucket=self.bucket, key=key)


class FakeKnowledgeDocumentRepository:
    """Store knowledge documents in process for tests."""

    def __init__(self) -> None:
        """Initialize an empty repository."""
        self._items: dict[int, KnowledgeDocument] = {}
        self._next_id = 1

    def create(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Insert a document and return it with a generated id."""
        new_id = self._next_id
        self._next_id += 1
        created = replace(document, id=new_id)
        self._items[new_id] = created
        return created

    def get(self, document_id: int) -> KnowledgeDocument | None:
        """Return a document by id when present."""
        return self._items.get(document_id)

    def get_by_content_hash(self, content_hash: str) -> KnowledgeDocument | None:
        """Return the document already holding this content, when there is one."""
        for document in self._items.values():
            if document.content_hash == content_hash:
                return document
        return None

    def update(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Replace the stored document; KeyError when the id is unknown."""
        if document.id not in self._items:
            raise KeyError(document.id)
        self._items[document.id] = document
        return document


class FakeDocumentIngestor:
    """Record what it was asked to ingest instead of calling an AI provider."""

    def __init__(self, *, page_count: int = 3, fails: bool = False) -> None:
        """Succeed with `page_count`, or raise DocumentIngestionError when `fails`."""
        self.page_count = page_count
        self.fails = fails
        self.ingested: list[tuple[KnowledgeDocument, bytes]] = []

    def ingest(self, document: KnowledgeDocument, data: bytes) -> IngestionOutcome:
        """Remember the call, then succeed or fail as configured."""
        self.ingested.append((document, data))
        if self.fails:
            raise DocumentIngestionError("fake ingestion failure")
        return IngestionOutcome(page_count=self.page_count)
