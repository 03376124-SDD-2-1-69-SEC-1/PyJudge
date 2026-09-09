"""Build an application wired entirely to fakes.

`create_app()` with no arguments builds SQL and R2 adapters, so every test that
drives HTTP goes through here instead: one place that decides what a test app is
made of, and no test that accidentally reaches real infrastructure.
"""

from __future__ import annotations

from fastapi import FastAPI

from greader.ai.app.repository import InMemoryVectorRepository, VectorRepository
from greader.config import DEFAULT_MAX_UPLOAD_SIZE_BYTES, Settings
from greader.core.assignments.ports import AssignmentRepository
from greader.core.generation.ports import GenerationClient, GenerationRepository
from greader.core.topics.ports import TopicRepository
from greader.core.uploads.ports import KnowledgeDocumentRepository, ObjectStorage
from greader.main import create_app
from tests.fakes.assignments import FakeAssignmentRepository
from tests.fakes.generation import FakeGenerationRepository
from tests.fakes.topics import FakeTopicRepository
from tests.fakes.uploads import FakeKnowledgeDocumentRepository, FakeObjectStorage


def fake_settings(
    max_upload_size_bytes: int = DEFAULT_MAX_UPLOAD_SIZE_BYTES,
) -> Settings:
    """Return settings that name no real database or bucket.

    Nothing dials these values: a test app is built from fakes, and the two
    health routes that would use them are not exercised here.
    """
    return Settings(
        database_url="postgresql+psycopg://unused:unused@localhost/unused",
        r2_endpoint_url="https://unused.r2.cloudflarestorage.com",
        r2_bucket_name="unused-bucket",
        r2_access_key_id="unused",
        r2_secret_access_key="unused",
        max_upload_size_bytes=max_upload_size_bytes,
    )


def build_app(
    *,
    topic_repository: TopicRepository | None = None,
    assignment_repository: AssignmentRepository | None = None,
    knowledge_document_repository: KnowledgeDocumentRepository | None = None,
    object_storage: ObjectStorage | None = None,
    generation_client: GenerationClient | None = None,
    generation_repository: GenerationRepository | None = None,
    vector_repository: VectorRepository | None = None,
    max_upload_size_bytes: int = DEFAULT_MAX_UPLOAD_SIZE_BYTES,
) -> FastAPI:
    """Return an app whose every port is backed by a fake."""
    if topic_repository is None:
        topic_repository = FakeTopicRepository()
    if assignment_repository is None:
        assignment_repository = FakeAssignmentRepository()
    if knowledge_document_repository is None:
        knowledge_document_repository = FakeKnowledgeDocumentRepository()
    if object_storage is None:
        object_storage = FakeObjectStorage()
    if generation_repository is None:
        generation_repository = FakeGenerationRepository()
    if vector_repository is None:
        vector_repository = InMemoryVectorRepository()

    return create_app(
        settings=fake_settings(max_upload_size_bytes=max_upload_size_bytes),
        topic_repository=topic_repository,
        assignment_repository=assignment_repository,
        knowledge_document_repository=knowledge_document_repository,
        object_storage=object_storage,
        generation_client=generation_client,
        generation_repository=generation_repository,
        vector_repository=vector_repository,
    )
