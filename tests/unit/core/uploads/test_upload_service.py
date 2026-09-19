"""Tests for upload application rules."""

from hashlib import sha256

import pytest

from greader.core.uploads.models import DocumentStatus
from greader.core.uploads.service import (
    EmptyUploadError,
    KnowledgeDocumentNotFoundError,
    UploadService,
    UploadTooLargeError,
)
from tests.fakes.uploads import FakeKnowledgeDocumentRepository, FakeObjectStorage


def _service(max_upload_size_bytes: int = 1024) -> UploadService:
    return UploadService(
        FakeObjectStorage(),
        FakeKnowledgeDocumentRepository(),
        max_upload_size_bytes=max_upload_size_bytes,
    )


def test_store_indexes_the_document_and_hashes_its_content() -> None:
    service = _service()

    document = service.store(filename="notes.txt", data=b"hello world")

    assert isinstance(document.id, int)
    assert document.filename == "notes.txt"
    assert document.object_key.startswith("uploads/")
    assert document.object_key.endswith("-notes.txt")
    assert document.content_hash == sha256(b"hello world").hexdigest()
    assert document.status is DocumentStatus.UPLOADED


def test_store_rejects_a_file_over_the_limit() -> None:
    service = _service(max_upload_size_bytes=4)

    with pytest.raises(UploadTooLargeError):
        service.store(filename="big.bin", data=b"12345")


def test_store_rejects_an_empty_file() -> None:
    service = _service()

    with pytest.raises(EmptyUploadError):
        service.store(filename="empty.txt", data=b"")


def test_store_strips_path_segments_from_the_filename() -> None:
    """A client-supplied name must not steer the object out of `uploads/`."""
    service = _service()

    document = service.store(filename="../../etc/passwd", data=b"x")

    assert document.filename == "passwd"
    assert document.object_key.startswith("uploads/")
    assert ".." not in document.object_key


def test_store_rejects_a_filename_that_is_only_a_path() -> None:
    service = _service()

    with pytest.raises(EmptyUploadError):
        service.store(filename="../", data=b"x")


def test_storing_identical_content_twice_returns_the_same_document() -> None:
    storage = FakeObjectStorage()
    service = UploadService(
        storage,
        FakeKnowledgeDocumentRepository(),
        max_upload_size_bytes=1024,
    )

    first = service.store(filename="notes.txt", data=b"same bytes")
    second = service.store(filename="notes-copy.txt", data=b"same bytes")

    assert second == first
    assert len(storage.objects) == 1


def test_get_missing_document_raises() -> None:
    service = _service()

    with pytest.raises(KnowledgeDocumentNotFoundError):
        service.get(999)
