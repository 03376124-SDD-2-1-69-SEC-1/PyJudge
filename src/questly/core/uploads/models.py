"""Domain representation of an uploaded knowledge document."""

from dataclasses import dataclass
from enum import StrEnum


class DocumentStatus(StrEnum):
    """Where a document is in the ingestion pipeline.

    The same four values the `core.knowledge_documents` CHECK constraint allows,
    declared here so an invalid status fails in the domain instead of at the
    database.
    """

    UPLOADED = "uploaded"
    INGESTING = "ingesting"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Where object storage put the bytes.

    `bucket` is deployment configuration, not a fact about the document, so it
    stops here and never reaches `KnowledgeDocument` or the HTTP response.
    """

    bucket: str
    key: str


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """A file an instructor uploaded, and the object key holding its bytes.

    `id` is `None` only before the repository has persisted the document — see
    KnowledgeDocumentRepository.create(). Anything a repository returns has a
    non-None id. `uploaded_by` is `None` only for rows that predate it (the
    seed corpus, ADR-0008); `page_count` stays `None` until ingestion has read
    the PDF.
    """

    filename: str
    object_key: str
    content_hash: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    uploaded_by: int | None = None
    page_count: int | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class StoredUpload:
    """What `UploadService.store` did with an upload.

    `created` is `False` when identical bytes were already on record, so the
    caller knows there is nothing new to ingest.
    """

    document: KnowledgeDocument
    created: bool


@dataclass(frozen=True, slots=True)
class IngestionOutcome:
    """What a successful ingestion learned about the document."""

    page_count: int
