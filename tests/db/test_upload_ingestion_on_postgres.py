"""OPS-28: an Instructor's upload is owned, ingested and picked on Postgres.

The app is built the way `main.py` builds it for production, with only the
settings, R2, the vector store and the AI ingestor swapped out and the database
pointed at the throwaway branch. The rows asserted below were written by
`SQLKnowledgeDocumentRepository`, and the T-03 picker reads them through
`SQLDocumentCatalog`. No AI provider is called.
"""

from dataclasses import replace

import pytest
from sqlalchemy import text

from questly.core.auth.models import Role, User
from questly.core.auth.service import hash_password
from questly.core.generation.models import DocumentSummary
from questly.core.uploads.ports import DocumentIngestor
from questly.database.core.auth_repository import SQLAuthRepository
from questly.database.core.document_catalog_repository import SQLDocumentCatalog
from questly.database.session import SessionFactory
from questly.main import create_app
from tests.fakes.app import fake_settings
from tests.fakes.uploads import FakeDocumentIngestor, FakeObjectStorage
from tests.fakes.vector import FakeVectorRepository
from tests.integration.forms import asgi_client, log_in

pytestmark = pytest.mark.postgres

PASSWORD = "correct horse battery"
LECTURE = {"file": ("lecture.pdf", b"%PDF-1.4 fake", "application/pdf")}


def _app_and_accounts(
    postgres_url: str, session_factory: SessionFactory, ingestor: DocumentIngestor
):
    app = create_app(
        settings=replace(fake_settings(), database_url=postgres_url),
        object_storage=FakeObjectStorage(),
        vector_repository=FakeVectorRepository(),
        document_ingestor=ingestor,
        secure_cookies=False,
    )
    users = SQLAuthRepository(session_factory)

    def account(email: str, role: Role) -> User:
        return users.create_user(
            User(
                email=email,
                full_name=email,
                password_hash=hash_password(PASSWORD),
                role=role,
                email_verified=True,
            )
        )

    teacher = account("somchai.p@kmitl.ac.th", Role.INSTRUCTOR)
    student = account("66010001@kmitl.ac.th", Role.STUDENT)
    return app, teacher, student


def _documents(session_factory: SessionFactory) -> list[tuple]:
    with session_factory() as session:
        rows = session.execute(
            text(
                "SELECT uploaded_by, status, page_count, filename "
                "FROM core.knowledge_documents ORDER BY id"
            )
        ).all()
    return [tuple(row) for row in rows]


@pytest.mark.anyio
@pytest.mark.usefixtures("empty_core_tables")
async def test_an_instructor_upload_is_owned_ready_and_in_the_picker(
    postgres_url: str, session_factory: SessionFactory
) -> None:
    ingestor = FakeDocumentIngestor(page_count=9)
    app, teacher, _ = _app_and_accounts(postgres_url, session_factory, ingestor)
    client = asgi_client(app)
    await log_in(client, teacher.email, PASSWORD)

    response = await client.post("/api/v1/uploads", files=LECTURE)

    assert response.status_code == 201
    assert response.json()["status"] == "uploaded"
    assert _documents(session_factory) == [(teacher.id, "ready", 9, "lecture.pdf")]
    assert SQLDocumentCatalog(session_factory).documents_of(teacher.id) == [
        DocumentSummary(response.json()["id"], "lecture.pdf", 9)
    ]


@pytest.mark.anyio
@pytest.mark.usefixtures("empty_core_tables")
async def test_a_failed_ingestion_is_stored_as_failed_and_not_in_the_picker(
    postgres_url: str, session_factory: SessionFactory
) -> None:
    app, teacher, _ = _app_and_accounts(
        postgres_url, session_factory, FakeDocumentIngestor(fails=True)
    )
    client = asgi_client(app)
    await log_in(client, teacher.email, PASSWORD)

    response = await client.post("/api/v1/uploads", files=LECTURE)

    assert response.status_code == 201
    assert _documents(session_factory) == [(teacher.id, "failed", None, "lecture.pdf")]
    assert SQLDocumentCatalog(session_factory).documents_of(teacher.id) == []


@pytest.mark.anyio
@pytest.mark.usefixtures("empty_core_tables")
async def test_a_student_upload_writes_no_row(
    postgres_url: str, session_factory: SessionFactory
) -> None:
    app, _, student = _app_and_accounts(
        postgres_url, session_factory, FakeDocumentIngestor()
    )
    client = asgi_client(app)
    await log_in(client, student.email, PASSWORD)

    response = await client.post("/api/v1/uploads", files=LECTURE)

    assert response.status_code == 403
    assert _documents(session_factory) == []
