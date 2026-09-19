"""In-memory ObjectStorage and KnowledgeDocumentRepository for tests."""

from __future__ import annotations

from dataclasses import replace

from greader.core.uploads.models import KnowledgeDocument, StoredObject

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
