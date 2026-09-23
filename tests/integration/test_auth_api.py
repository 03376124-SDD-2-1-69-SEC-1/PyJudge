"""HTTP tests for /api/v1/auth and the 503 production wiring."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.core.auth.models import Role
from greader.integrations.email import StubEmailSender
from greader.main import create_app
from tests.fakes.app import build_app, fake_settings
from tests.fakes.assignments import FakeAssignmentRepository
from tests.fakes.auth import DEFAULT_PASSWORD, FakeAuthRepository, seed_user
from tests.fakes.generation import FakeGenerationRepository
from tests.fakes.topics import FakeTopicRepository
from tests.fakes.uploads import FakeKnowledgeDocumentRepository, FakeObjectStorage
from tests.fakes.vector import FakeVectorRepository

SIGN_UP = {
    "full_name": "Somchai Prasert",
    "email": "somchai@kmitl.ac.th",
    "password": "correct horse",
    "confirm_password": "correct horse",
}


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


@pytest.mark.anyio
async def test_sign_up_verify_login_me_logout_round_trip() -> None:
    mailer = StubEmailSender()
    async with _client(build_app(verification_mailer=mailer)) as client:
        created = await client.post("/api/v1/auth/signup", json=SIGN_UP)
        token = mailer.sent[-1][1].split("token=", 1)[1]
        verified = await client.post("/api/v1/auth/verify", json={"token": token})
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": SIGN_UP["email"], "password": SIGN_UP["password"]},
        )
        me = await client.get("/api/v1/auth/me")
        logout = await client.post("/api/v1/auth/logout")
        after = await client.get("/api/v1/auth/me")

    assert created.status_code == 201
    assert created.json()["role"] == "student"
    assert verified.json()["email_verified"] is True
    assert login.status_code == 200
    assert login.json()["landing"] == "classrooms"
    assert me.json()["email"] == SIGN_UP["email"]
    assert logout.status_code == 204
    assert after.status_code == 401


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("override", "status", "code"),
    [
        ({"email": "somchai@gmail.com"}, 422, "not_kmitl_email"),
        ({"password": "short", "confirm_password": "short"}, 422, "password_too_short"),
        ({"confirm_password": "different one"}, 422, "password_mismatch"),
        ({"wants_instructor": True}, 422, "faculty_required"),
    ],
)
async def test_sign_up_errors(override: dict, status: int, code: str) -> None:
    async with _client(build_app()) as client:
        response = await client.post(
            "/api/v1/auth/signup", json={**SIGN_UP, **override}
        )

    assert response.status_code == status
    assert response.json()["detail"]["code"] == code


@pytest.mark.anyio
async def test_sign_up_twice_is_a_conflict() -> None:
    async with _client(build_app()) as client:
        await client.post("/api/v1/auth/signup", json=SIGN_UP)
        response = await client.post("/api/v1/auth/signup", json=SIGN_UP)

    assert response.status_code == 409


@pytest.mark.anyio
async def test_verify_rejects_an_unknown_token() -> None:
    async with _client(build_app()) as client:
        response = await client.post("/api/v1/auth/verify", json={"token": "nope"})

    assert response.status_code == 400


@pytest.mark.anyio
async def test_resend_always_answers_202() -> None:
    async with _client(build_app()) as client:
        response = await client.post(
            "/api/v1/auth/verify/resend", json={"email": "nobody@kmitl.ac.th"}
        )

    assert response.status_code == 202


@pytest.mark.anyio
async def test_login_errors() -> None:
    repository = FakeAuthRepository()
    seed_user(repository, email="u@kmitl.ac.th", full_name="U", verified=False)
    async with _client(build_app(auth_repository=repository)) as client:
        wrong = await client.post(
            "/api/v1/auth/login", json={"email": "u@kmitl.ac.th", "password": "nope"}
        )
        unverified = await client.post(
            "/api/v1/auth/login",
            json={"email": "u@kmitl.ac.th", "password": DEFAULT_PASSWORD},
        )

    assert wrong.status_code == 401
    assert unverified.json()["detail"]["code"] == "email_not_verified"


@pytest.mark.anyio
async def test_instructor_request_by_a_student_then_a_duplicate() -> None:
    repository = FakeAuthRepository()
    seed_user(repository, email="s@kmitl.ac.th", full_name="S")
    async with _client(build_app(auth_repository=repository)) as client:
        await client.post(
            "/api/v1/auth/login",
            json={"email": "s@kmitl.ac.th", "password": DEFAULT_PASSWORD},
        )
        first = await client.post(
            "/api/v1/auth/instructor-requests", json={"faculty": "Science"}
        )
        second = await client.post(
            "/api/v1/auth/instructor-requests", json={"faculty": "Science"}
        )

    assert first.status_code == 201
    assert first.json()["status"] == "pending"
    assert second.status_code == 409


@pytest.mark.anyio
async def test_instructor_request_is_forbidden_to_an_instructor() -> None:
    repository = FakeAuthRepository()
    seed_user(repository, email="t@kmitl.ac.th", full_name="T", role=Role.INSTRUCTOR)
    async with _client(build_app(auth_repository=repository)) as client:
        await client.post(
            "/api/v1/auth/login",
            json={"email": "t@kmitl.ac.th", "password": DEFAULT_PASSWORD},
        )
        response = await client.post(
            "/api/v1/auth/instructor-requests", json={"faculty": "Science"}
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_production_wiring_answers_503_until_the_schema_lands() -> None:
    app = create_app(
        settings=fake_settings(),
        topic_repository=FakeTopicRepository(),
        assignment_repository=FakeAssignmentRepository(),
        knowledge_document_repository=FakeKnowledgeDocumentRepository(),
        object_storage=FakeObjectStorage(),
        generation_repository=FakeGenerationRepository(),
        vector_repository=FakeVectorRepository(),
    )
    async with _client(app) as client:
        response = await client.post("/api/v1/auth/signup", json=SIGN_UP)
        docs = await client.get("/openapi.json")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "not_persisted_yet"
    assert "/api/v1/auth/signup" in docs.json()["paths"]
