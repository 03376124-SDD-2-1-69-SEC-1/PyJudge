"""Tests for upload application rules."""

import logging
from dataclasses import replace
from hashlib import sha256

import pytest

from questly.core.auth.models import Actor, PermissionDeniedError, Role
from questly.core.uploads.models import (
    DocumentStatus,
    IngestionOutcome,
    KnowledgeDocument,
)
from questly.core.uploads.service import (
    EmptyUploadError,
    KnowledgeDocumentNotFoundError,
    UploadService,
    UploadTooLargeError,
)
from tests.fakes.uploads import (
    FakeDocumentIngestor,
    FakeKnowledgeDocumentRepository,
    FakeObjectStorage,
)

INSTRUCTOR = Actor(
    user_id=7, role=Role.INSTRUCTOR, full_name="Somchai", email="s@kmitl.ac.th"
)


def _service(
    max_upload_size_bytes: int = 1024,
    *,
    storage: FakeObjectStorage | None = None,
    repository: FakeKnowledgeDocumentRepository | None = None,
    ingestor: FakeDocumentIngestor | None = None,
) -> UploadService:
    return UploadService(
        FakeObjectStorage() if storage is None else storage,
        FakeKnowledgeDocumentRepository() if repository is None else repository,
        FakeDocumentIngestor() if ingestor is None else ingestor,
        max_upload_size_bytes=max_upload_size_bytes,
    )


def test_store_indexes_the_document_and_hashes_its_content() -> None:
    service = _service()

    stored = service.store(INSTRUCTOR, filename="notes.txt", data=b"hello world")

    document = stored.document
    assert stored.created
    assert isinstance(document.id, int)
    assert document.filename == "notes.txt"
    assert document.object_key.startswith("uploads/")
    assert document.object_key.endswith("-notes.txt")
    assert document.content_hash == sha256(b"hello world").hexdigest()
    assert document.status is DocumentStatus.UPLOADED


def test_store_records_who_uploaded_the_document() -> None:
    service = _service()

    stored = service.store(INSTRUCTOR, filename="notes.txt", data=b"hello world")

    assert stored.document.uploaded_by == INSTRUCTOR.user_id
    assert service.get(stored.document.id).uploaded_by == INSTRUCTOR.user_id


@pytest.mark.parametrize("role", [Role.STUDENT, Role.ADMIN])
def test_only_an_instructor_may_upload(role: Role) -> None:
    storage = FakeObjectStorage()
    service = _service(storage=storage)

    with pytest.raises(PermissionDeniedError):
        service.store(replace(INSTRUCTOR, role=role), filename="a.pdf", data=b"x")

    assert storage.objects == {}


def test_store_rejects_a_file_over_the_limit() -> None:
    service = _service(max_upload_size_bytes=4)

    with pytest.raises(UploadTooLargeError):
        service.store(INSTRUCTOR, filename="big.bin", data=b"12345")


def test_store_rejects_an_empty_file() -> None:
    service = _service()

    with pytest.raises(EmptyUploadError):
        service.store(INSTRUCTOR, filename="empty.txt", data=b"")


def test_store_strips_path_segments_from_the_filename() -> None:
    """A client-supplied name must not steer the object out of `uploads/`."""
    service = _service()

    document = service.store(
        INSTRUCTOR, filename="../../etc/passwd", data=b"x"
    ).document

    assert document.filename == "passwd"
    assert document.object_key.startswith("uploads/")
    assert ".." not in document.object_key


def test_store_rejects_a_filename_that_is_only_a_path() -> None:
    service = _service()

    with pytest.raises(EmptyUploadError):
        service.store(INSTRUCTOR, filename="../", data=b"x")


def test_storing_identical_content_twice_returns_the_same_document() -> None:
    storage = FakeObjectStorage()
    service = _service(storage=storage)

    first = service.store(INSTRUCTOR, filename="notes.txt", data=b"same bytes")
    second = service.store(INSTRUCTOR, filename="notes-copy.txt", data=b"same bytes")

    assert first.created
    assert not second.created
    assert second.document == first.document
    assert len(storage.objects) == 1


def test_get_missing_document_raises() -> None:
    service = _service()

    with pytest.raises(KnowledgeDocumentNotFoundError):
        service.get(999)


def _uploaded(service: UploadService, data: bytes = b"%PDF fake") -> KnowledgeDocument:
    return service.store(INSTRUCTOR, filename="lecture.pdf", data=data).document


def test_ingest_moves_the_document_to_ready_with_its_page_count() -> None:
    ingestor = FakeDocumentIngestor(page_count=12)
    service = _service(ingestor=ingestor)
    document = _uploaded(service)

    service.ingest(document.id, b"%PDF fake")

    ready = service.get(document.id)
    assert ready.status is DocumentStatus.READY
    assert ready.page_count == 12
    assert ready.uploaded_by == INSTRUCTOR.user_id
    assert ingestor.ingested == [(document, b"%PDF fake")]


def test_the_document_is_ingesting_while_the_ingestor_runs() -> None:
    repository = FakeKnowledgeDocumentRepository()
    seen: list[DocumentStatus] = []

    class Watching:
        def ingest(self, document: KnowledgeDocument, data: bytes) -> IngestionOutcome:
            seen.append(repository.get(document.id).status)
            return IngestionOutcome(page_count=1)

    service = UploadService(
        FakeObjectStorage(), repository, Watching(), max_upload_size_bytes=1024
    )
    document = _uploaded(service)

    service.ingest(document.id, b"%PDF fake")

    assert seen == [DocumentStatus.INGESTING]


def test_a_failing_ingestor_marks_the_document_failed_and_logs_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = _service(ingestor=FakeDocumentIngestor(fails=True))
    document = _uploaded(service)

    with caplog.at_level(logging.ERROR):
        service.ingest(document.id, b"%PDF fake")

    failed = service.get(document.id)
    assert failed.status is DocumentStatus.FAILED
    assert failed.page_count is None
    assert f"knowledge document {document.id}" in caplog.text


def test_any_exception_from_the_ingestor_marks_the_document_failed() -> None:
    class Broken:
        def ingest(self, document: KnowledgeDocument, data: bytes) -> IngestionOutcome:
            raise RuntimeError("database went away")

    service = UploadService(
        FakeObjectStorage(),
        FakeKnowledgeDocumentRepository(),
        Broken(),
        max_upload_size_bytes=1024,
    )
    document = _uploaded(service)

    service.ingest(document.id, b"%PDF fake")

    assert service.get(document.id).status is DocumentStatus.FAILED


def test_a_document_is_not_left_ingesting_when_saving_ready_fails() -> None:
    class FailsOnceOnReady(FakeKnowledgeDocumentRepository):
        def update(self, document: KnowledgeDocument) -> KnowledgeDocument:
            if document.status is DocumentStatus.READY:
                raise RuntimeError("connection reset")
            return super().update(document)

    service = _service(repository=FailsOnceOnReady())
    document = _uploaded(service)

    service.ingest(document.id, b"%PDF fake")

    assert service.get(document.id).status is DocumentStatus.FAILED


def test_ingesting_an_unknown_document_raises() -> None:
    service = _service()

    with pytest.raises(KnowledgeDocumentNotFoundError):
        service.ingest(999, b"%PDF fake")
