"""HTTP tests for the Admin API and its authorization boundary."""

import pytest
from httpx import ASGITransport, AsyncClient

from questly.core.auth.models import Actor, InstructorRequest, Role
from tests.fakes.admin import FakeAdminRepository, FakeSystemHealthChecker
from tests.fakes.app import build_app
from tests.fakes.auth import (
    DEFAULT_NOW,
    DEFAULT_PASSWORD,
    FakeAuthRepository,
    seed_user,
)
from tests.fakes.generation import FakeGenerationClient, binary_search_response

ADMIN = "admin@kmitl.ac.th"
INSTRUCTOR = "instructor@kmitl.ac.th"
STUDENT = "66010001@kmitl.ac.th"


class AdminApi:
    def __init__(self) -> None:
        self.auth = FakeAuthRepository()
        self.admin = seed_user(
            self.auth, email=ADMIN, full_name="Admin", role=Role.ADMIN
        )
        self.instructor = seed_user(
            self.auth, email=INSTRUCTOR, full_name="Instructor", role=Role.INSTRUCTOR
        )
        self.student = seed_user(self.auth, email=STUDENT, full_name="Nattapong Suwan")
        self.settings = FakeAdminRepository()
        self.health = FakeSystemHealthChecker()
        self.generation_client = FakeGenerationClient(binary_search_response())
        self.app = build_app(
            auth_repository=self.auth,
            admin_repository=self.settings,
            system_health_checker=self.health,
            generation_client=self.generation_client,
        )

    async def client_for(self, email: str) -> AsyncClient:
        client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://testserver"
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": DEFAULT_PASSWORD},
        )
        assert response.status_code == 200
        return client


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/v1/admin/instructor-requests", None),
        ("POST", "/api/v1/admin/instructor-requests/1/approve", None),
        ("POST", "/api/v1/admin/instructor-requests/1/reject", None),
        ("GET", "/api/v1/admin/users", None),
        ("PATCH", "/api/v1/admin/users/1", {"role": "student"}),
        ("POST", "/api/v1/admin/users/1/deactivate", None),
        ("GET", "/api/v1/admin/ai-settings", None),
        ("PUT", "/api/v1/admin/ai-settings", {"daily_quota": 10}),
        ("GET", "/api/v1/admin/status", None),
    ],
)
async def test_admin_endpoints_require_admin_role(
    method: str, path: str, body: dict | None
) -> None:
    api = AdminApi()
    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://testserver"
    ) as anonymous:
        response = await anonymous.request(method, path, json=body)
        assert response.status_code == 401

    for email in (INSTRUCTOR, STUDENT):
        client = await api.client_for(email)
        response = await client.request(method, path, json=body)
        await client.aclose()
        assert response.status_code == 403


@pytest.mark.anyio
async def test_admin_can_approve_or_reject_instructor_requests() -> None:
    api = AdminApi()
    approved = api.auth.create_instructor_request(
        InstructorRequest(api.student.id, "Engineering", DEFAULT_NOW)
    )
    rejected_user = seed_user(
        api.auth, email="66010002@kmitl.ac.th", full_name="Pimchanok Wong"
    )
    rejected = api.auth.create_instructor_request(
        InstructorRequest(rejected_user.id, "Science", DEFAULT_NOW)
    )
    client = await api.client_for(ADMIN)

    pending = await client.get("/api/v1/admin/instructor-requests")
    approval = await client.post(
        f"/api/v1/admin/instructor-requests/{approved.id}/approve"
    )
    rejection = await client.post(
        f"/api/v1/admin/instructor-requests/{rejected.id}/reject"
    )

    assert [item["id"] for item in pending.json()] == [approved.id, rejected.id]
    assert pending.json()[0]["full_name"] == api.student.full_name
    assert pending.json()[0]["faculty"] == "Engineering"
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"
    assert approval.json()["reviewed_by"] == api.admin.id
    assert approval.json()["reviewed_at"] is not None
    assert api.auth.get_user(api.student.id).role is Role.INSTRUCTOR
    assert rejection.json()["status"] == "rejected"
    assert api.auth.get_user(rejected_user.id).role is Role.STUDENT

    duplicate = await client.post(
        f"/api/v1/admin/instructor-requests/{approved.id}/reject"
    )
    missing = await client.post("/api/v1/admin/instructor-requests/99999/approve")
    assert duplicate.status_code == 409
    assert missing.status_code == 404
    await client.aclose()


@pytest.mark.anyio
async def test_admin_endpoints_validate_missing_and_invalid_inputs() -> None:
    api = AdminApi()
    client = await api.client_for(ADMIN)

    invalid_role_filter = await client.get(
        "/api/v1/admin/users", params={"role": "superuser"}
    )
    invalid_page = await client.get("/api/v1/admin/users", params={"page": 0})
    missing_role_target = await client.patch(
        "/api/v1/admin/users/99999", json={"role": "student"}
    )
    invalid_role = await client.patch(
        f"/api/v1/admin/users/{api.student.id}", json={"role": "superuser"}
    )
    missing_deactivation_target = await client.post(
        "/api/v1/admin/users/99999/deactivate"
    )
    invalid_quota = await client.put(
        "/api/v1/admin/ai-settings", json={"daily_quota": 0}
    )
    null_quota = await client.put(
        "/api/v1/admin/ai-settings", json={"daily_quota": None}
    )

    assert invalid_role_filter.status_code == 422
    assert invalid_page.status_code == 422
    assert missing_role_target.status_code == 404
    assert invalid_role.status_code == 422
    assert missing_deactivation_target.status_code == 404
    assert invalid_quota.status_code == 422
    assert null_quota.status_code == 422
    await client.aclose()


@pytest.mark.anyio
async def test_admin_can_search_change_role_and_deactivate_users() -> None:
    api = AdminApi()
    client = await api.client_for(ADMIN)
    student_client = await api.client_for(STUDENT)

    search = await client.get(
        "/api/v1/admin/users", params={"q": "NATTAPONG", "role": "student"}
    )
    role_change = await client.patch(
        f"/api/v1/admin/users/{api.student.id}", json={"role": "instructor"}
    )
    deactivation = await client.post(f"/api/v1/admin/users/{api.student.id}/deactivate")
    own_role_change = await client.patch(
        f"/api/v1/admin/users/{api.admin.id}", json={"role": "student"}
    )
    own_deactivation = await client.post(
        f"/api/v1/admin/users/{api.admin.id}/deactivate"
    )
    inactive_session = await student_client.get("/api/v1/auth/me")

    assert search.status_code == 200
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["full_name"] == api.student.full_name
    assert role_change.status_code == 200
    assert role_change.json()["role"] == "instructor"
    assert deactivation.status_code == 200
    assert deactivation.json()["is_active"] is False
    assert own_role_change.status_code == 400
    assert own_deactivation.status_code == 400
    assert inactive_session.status_code == 401
    await client.aclose()
    await student_client.aclose()


@pytest.mark.anyio
async def test_ai_settings_update_changes_generation_quota() -> None:
    api = AdminApi()
    client = await api.client_for(ADMIN)

    changed = await client.put(
        "/api/v1/admin/ai-settings",
        json={
            "model": api.settings.settings.model,
            "daily_quota": 7,
            "max_pages": 12,
            "require_citations": False,
        },
    )
    model_rejected = await client.put(
        "/api/v1/admin/ai-settings", json={"model": "not-configured"}
    )
    current = await client.get("/api/v1/admin/ai-settings")
    quota = api.app.state.generation_service.quota(
        Actor(
            user_id=api.instructor.id,
            role=Role.INSTRUCTOR,
            full_name=api.instructor.full_name,
            email=api.instructor.email,
        )
    )

    assert changed.status_code == 200
    assert changed.json()["daily_quota"] == 7
    assert changed.json()["max_pages"] == 12
    assert changed.json()["require_citations"] is False
    assert changed.json()["usage_this_month"] == 5
    assert model_rejected.status_code == 422
    assert current.json()["daily_quota"] == 7
    assert quota.limit == 7
    await client.aclose()


@pytest.mark.anyio
async def test_generation_is_rejected_after_updated_daily_quota_is_used() -> None:
    api = AdminApi()
    instructor = Actor(
        user_id=api.instructor.id,
        role=Role.INSTRUCTOR,
        full_name=api.instructor.full_name,
        email=api.instructor.email,
    )
    classroom = api.app.state.classroom_service.create(
        instructor,
        course_code="01076001",
        course_name="Programming I",
        section="1",
        semester="1/2569",
    )
    admin = await api.client_for(ADMIN)

    settings = await admin.put("/api/v1/admin/ai-settings", json={"daily_quota": 1})
    client = await api.client_for(INSTRUCTOR)
    first = await client.post(
        f"/api/v1/classrooms/{classroom.id}/drafts",
        json={"prompt": "Binary search"},
    )
    second = await client.post(
        f"/api/v1/classrooms/{classroom.id}/drafts",
        json={"prompt": "Another problem"},
    )

    assert settings.status_code == 200
    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "quota_exceeded"
    assert len(api.generation_client.requests) == 1
    await admin.aclose()
    await client.aclose()


@pytest.mark.anyio
async def test_system_status_reports_all_six_adapters() -> None:
    api = AdminApi()
    client = await api.client_for(ADMIN)

    response = await client.get("/api/v1/admin/status")

    assert response.status_code == 200
    assert [service["name"] for service in response.json()["services"]] == [
        "web application",
        "database",
        "PDF processing",
        "AI generation",
        "code execution sandbox",
        "email delivery",
    ]
    await client.aclose()
