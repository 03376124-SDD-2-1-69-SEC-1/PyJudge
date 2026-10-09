"""`create_app` with nothing injected persists to Postgres (OPS-15).

Built the way production builds it — only settings, R2 and the vector store
swapped out — and pointed at the throwaway branch. The services on `app.state`
then write through whatever `main.py` wired, so rows in the database prove the
SQL adapters are the ones in use. Fake-backed HTTP tests live in
`test_admin_api.py`.
"""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from questly.core.admin.domain import AISettingsUpdate
from questly.core.auth.models import Actor, InstructorRequest, Role, User
from questly.core.auth.service import hash_password
from questly.database.core.admin_repository import SQLAdminRepository
from questly.database.core.auth_repository import SQLAuthRepository
from questly.database.core.draft_repository import SQLDraftRepository
from questly.database.session import SessionFactory
from questly.integrations.email import StubEmailSender
from questly.main import create_app
from tests.fakes.app import fake_settings
from tests.fakes.uploads import FakeObjectStorage
from tests.fakes.vector import FakeVectorRepository

pytestmark = pytest.mark.postgres


@pytest.mark.usefixtures("empty_core_tables")
def test_sign_up_verify_and_log_in_write_to_postgres(
    postgres_url: str, session_factory: SessionFactory
) -> None:
    mailer = StubEmailSender()
    app = create_app(
        settings=replace(fake_settings(), database_url=postgres_url),
        verification_mailer=mailer,
        object_storage=FakeObjectStorage(),
        vector_repository=FakeVectorRepository(),
    )
    auth = app.state.auth_service

    auth.sign_up(
        full_name="Somchai Prasert",
        email="somchai@kmitl.ac.th",
        password="correct horse",
        confirm_password="correct horse",
        wants_instructor=True,
        faculty="Engineering",
    )
    auth.verify_email(mailer.sent[-1][1].split("token=", 1)[1])
    login = auth.log_in(email="somchai@kmitl.ac.th", password="correct horse")

    assert auth.resolve_session(login.token).full_name == "Somchai Prasert"
    with session_factory() as session:
        stored = session.execute(
            text(
                "SELECT u.full_name, u.email_verified_at IS NOT NULL, "
                "(SELECT count(*) FROM core.sessions s WHERE s.user_id = u.id), "
                "(SELECT faculty FROM core.instructor_requests r "
                " WHERE r.user_id = u.id) "
                "FROM core.users u"
            )
        ).one()
    assert tuple(stored) == ("Somchai Prasert", True, 1, "Engineering")


@pytest.mark.usefixtures("empty_core_tables")
def test_admin_routes_persist_settings_and_generation_enforces_quota(
    postgres_url: str, session_factory: SessionFactory
) -> None:
    settings_repository = SQLAdminRepository(session_factory)
    original_settings = settings_repository.get_ai_settings()
    auth_repository = SQLAuthRepository(session_factory)
    admin = auth_repository.create_user(
        User(
            email="admin@kmitl.ac.th",
            full_name="Admin",
            password_hash=hash_password("admin-pass"),
            role=Role.ADMIN,
            email_verified=True,
        )
    )
    applicant = auth_repository.create_user(
        User(
            email="applicant@kmitl.ac.th",
            full_name="Applicant",
            password_hash=hash_password("applicant-pass"),
            email_verified=True,
        )
    )
    request = auth_repository.create_instructor_request(
        InstructorRequest(applicant.id, "Engineering", datetime.now(UTC))
    )
    app = create_app(
        settings=replace(fake_settings(), database_url=postgres_url),
        object_storage=FakeObjectStorage(),
        vector_repository=FakeVectorRepository(),
    )

    try:
        with TestClient(app) as client:
            admin_login = client.post(
                "/api/v1/auth/login",
                json={"email": admin.email, "password": "admin-pass"},
            )
            approved = client.post(
                f"/api/v1/admin/instructor-requests/{request.id}/approve"
            )
            changed_settings = client.put(
                "/api/v1/admin/ai-settings", json={"daily_quota": 1}
            )
            read_settings = client.get("/api/v1/admin/ai-settings")

            assert admin_login.status_code == 200
            assert approved.status_code == 200
            assert approved.json()["reviewed_by"] == admin.id
            assert approved.json()["reviewed_at"] is not None
            assert changed_settings.status_code == 200
            assert read_settings.json()["daily_quota"] == 1
            assert auth_repository.get_user(applicant.id).role is Role.INSTRUCTOR

            instructor = Actor(
                user_id=applicant.id,
                role=Role.INSTRUCTOR,
                full_name=applicant.full_name,
                email=applicant.email,
            )
            classroom = app.state.classroom_service.create(
                instructor,
                course_code="01076001",
                course_name="Programming I",
                section="1",
                semester="1/2569",
            )
            SQLDraftRepository(session_factory).record_generation(
                applicant.id, datetime.now(UTC)
            )
            quota = app.state.generation_service.quota(instructor)
            assert quota.used == quota.limit == 1

            instructor_login = client.post(
                "/api/v1/auth/login",
                json={"email": applicant.email, "password": "applicant-pass"},
            )
            exhausted = client.post(
                f"/api/v1/classrooms/{classroom.id}/drafts",
                json={"prompt": "A binary search problem"},
            )

            assert instructor_login.status_code == 200
            assert exhausted.status_code == 429
            assert exhausted.json()["detail"]["code"] == "quota_exceeded"
    finally:
        settings_repository.update_ai_settings(
            AISettingsUpdate(
                model=original_settings.model,
                daily_quota=original_settings.daily_quota,
                max_pages=original_settings.max_pages,
                require_citations=original_settings.require_citations,
            )
        )
