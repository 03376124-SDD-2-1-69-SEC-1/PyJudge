"""Admin API routes (ADR-0007 §8)."""

from fastapi import APIRouter, Query, Request

from questly.core.admin.domain import (
    AISettings,
    AISettingsUpdate,
    SystemStatusResponse,
    UserRole,
)
from questly.core.admin.schemas import (
    InstructorRequestResponse,
    UserAdminResponse,
    UserPaginatedResponse,
    UserRoleUpdate,
)
from questly.core.admin.service import AdminService
from questly.core.auth.current import current_actor
from questly.core.auth.models import (
    InstructorRequest,
    InstructorRequestStatus,
    User,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _service(request: Request) -> AdminService:
    return request.app.state.admin_service


def _request_response(
    instructor_request: InstructorRequest, user: User
) -> InstructorRequestResponse:
    return InstructorRequestResponse(
        id=instructor_request.id,
        user_id=instructor_request.user_id,
        full_name=user.full_name,
        email=user.email,
        faculty=instructor_request.faculty,
        status=instructor_request.status,
        reviewed_by=instructor_request.reviewed_by,
        reviewed_at=instructor_request.reviewed_at,
        requested_at=instructor_request.requested_at,
    )


@router.get("/instructor-requests", response_model=list[InstructorRequestResponse])
def list_instructor_requests(
    request: Request,
    status_filter: InstructorRequestStatus | None = Query(  # noqa: B008 — FastAPI
        InstructorRequestStatus.PENDING, alias="status"
    ),
) -> list[InstructorRequestResponse]:
    actor = current_actor(request)
    return [
        _request_response(instructor_request, user)
        for instructor_request, user in _service(request).list_instructor_requests(
            actor, status_filter=status_filter
        )
    ]


@router.post(
    "/instructor-requests/{request_id}/approve",
    response_model=InstructorRequestResponse,
)
def approve_instructor_request(
    request: Request, request_id: int
) -> InstructorRequestResponse:
    actor = current_actor(request)
    instructor_request, user = _service(request).approve_instructor_request(
        actor, request_id=request_id
    )
    return _request_response(instructor_request, user)


@router.post(
    "/instructor-requests/{request_id}/reject",
    response_model=InstructorRequestResponse,
)
def reject_instructor_request(
    request: Request, request_id: int
) -> InstructorRequestResponse:
    actor = current_actor(request)
    instructor_request, user = _service(request).reject_instructor_request(
        actor, request_id=request_id
    )
    return _request_response(instructor_request, user)


@router.get("/users", response_model=UserPaginatedResponse)
def list_users(
    request: Request,
    q: str | None = Query(None, max_length=100),
    role: UserRole | None = None,
    page: int = Query(1, ge=1),
) -> UserPaginatedResponse:
    actor = current_actor(request)
    items, total = _service(request).list_users(
        actor, q=q, role=role, page=page, page_size=25
    )
    return UserPaginatedResponse(
        items=[
            UserAdminResponse(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=user.role.value,
                is_active=user.is_active,
            )
            for user in items
        ],
        total=total,
        page=page,
        page_size=25,
    )


@router.patch("/users/{user_id}", response_model=UserAdminResponse)
def update_user_role(
    request: Request, user_id: int, body: UserRoleUpdate
) -> UserAdminResponse:
    actor = current_actor(request)
    user = _service(request).update_user_role(
        actor, user_id=user_id, new_role=body.role
    )
    return UserAdminResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
    )


@router.post("/users/{user_id}/deactivate", response_model=UserAdminResponse)
def deactivate_user(request: Request, user_id: int) -> UserAdminResponse:
    actor = current_actor(request)
    user = _service(request).deactivate_user(actor, user_id=user_id)
    return UserAdminResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
    )


@router.get("/ai-settings", response_model=AISettings)
def get_ai_settings(request: Request) -> AISettings:
    actor = current_actor(request)
    return _service(request).get_ai_settings(actor)


@router.put("/ai-settings", response_model=AISettings)
def update_ai_settings(request: Request, body: AISettingsUpdate) -> AISettings:
    actor = current_actor(request)
    return _service(request).update_ai_settings(actor, body)


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(request: Request) -> SystemStatusResponse:
    actor = current_actor(request)
    return _service(request).get_system_status(actor)
