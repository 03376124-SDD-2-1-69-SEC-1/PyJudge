from dataclasses import replace

from fastapi import HTTPException, status

from questly.core.admin.domain import (
    AISettings,
    AISettingsUpdate,
    SystemStatusResponse,
    UserRole,
)
from questly.core.admin.ports import AdminRepository, SystemHealthChecker
from questly.core.auth.models import (
    Actor,
    InstructorRequest,
    InstructorRequestStatus,
    PermissionDeniedError,
    Role,
    User,
)
from questly.core.auth.ports import AuthRepository


class AdminService:
    def __init__(
        self,
        admin_repo: AdminRepository | None,
        auth_repo: AuthRepository,
        health_checker: SystemHealthChecker | None = None,
        allowed_models: tuple[str, ...] = (),
    ):
        self.admin_repo = admin_repo
        self.auth_repo = auth_repo
        self.health_checker = health_checker
        self.allowed_models = allowed_models

    # --- Instructor Requests ---
    def list_instructor_requests(
        self,
        actor: Actor,
        status_filter: InstructorRequestStatus | None = InstructorRequestStatus.PENDING,
    ) -> list[tuple[InstructorRequest, User]]:
        self._require_admin(actor)
        requests = self.auth_repo.list_instructor_requests(status=status_filter)
        return [
            self._request_and_user(instructor_request)
            for instructor_request in requests
        ]

    def approve_instructor_request(
        self, actor: Actor, request_id: int
    ) -> tuple[InstructorRequest, User]:
        self._require_admin(actor)
        request = self._review_instructor_request(
            request_id, actor.user_id, approve=True
        )
        return self._request_and_user(request)

    def reject_instructor_request(
        self, actor: Actor, request_id: int
    ) -> tuple[InstructorRequest, User]:
        self._require_admin(actor)
        request = self._review_instructor_request(
            request_id, actor.user_id, approve=False
        )
        return self._request_and_user(request)

    # --- User Management ---
    def list_users(
        self,
        actor: Actor,
        q: str | None = None,
        role: UserRole | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[User], int]:
        self._require_admin(actor)
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be at least 1",
            )
        role_val = role.value if role else None
        return self.auth_repo.search_users(
            q=q, role=role_val, page=page, page_size=page_size
        )

    def update_user_role(self, actor: Actor, user_id: int, new_role: UserRole) -> User:
        self._require_admin(actor)
        if user_id == actor.user_id and new_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote your own admin role",
            )
        user = self._get_user(user_id)
        return self.auth_repo.update_user(replace(user, role=Role(new_role.value)))

    def deactivate_user(self, actor: Actor, user_id: int) -> User:
        self._require_admin(actor)
        if user_id == actor.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own admin account",
            )
        user = self._get_user(user_id)
        deactivated = self.auth_repo.update_user(replace(user, is_active=False))
        self.auth_repo.revoke_sessions_of(user_id)
        return deactivated

    # --- AI Settings ---
    def get_ai_settings(self, actor: Actor) -> AISettings:
        self._require_admin(actor)
        admin_repo = self._require_admin_repository()
        settings = admin_repo.get_ai_settings()
        return settings.model_copy(
            update={"usage_this_month": admin_repo.get_usage_this_month()}
        )

    def update_ai_settings(
        self, actor: Actor, settings: AISettingsUpdate
    ) -> AISettings:
        self._require_admin(actor)
        if settings.model is not None and settings.model not in self.allowed_models:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Model is not in the configured allowlist",
            )
        admin_repo = self._require_admin_repository()
        saved = admin_repo.update_ai_settings(settings)
        return saved.model_copy(
            update={"usage_this_month": admin_repo.get_usage_this_month()}
        )

    # --- System Status ---
    def get_system_status(self, actor: Actor) -> SystemStatusResponse:
        self._require_admin(actor)
        if not self.health_checker:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Health checker unavailable",
            )
        return self.health_checker.check_services_health()

    def _require_admin(self, actor: Actor) -> None:
        if actor.role is not Role.ADMIN:
            raise PermissionDeniedError

    def _get_user(self, user_id: int) -> User:
        user = self.auth_repo.get_user(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    def _require_admin_repository(self) -> AdminRepository:
        if self.admin_repo is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Admin settings repository is not wired",
            )
        return self.admin_repo

    def _review_instructor_request(
        self, request_id: int, reviewer_id: int, *, approve: bool
    ) -> InstructorRequest:
        try:
            return self.auth_repo.review_instructor_request(
                request_id=request_id, reviewer_id=reviewer_id, approve=approve
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instructor request not found",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Instructor request has already been reviewed",
            ) from exc

    def _request_and_user(
        self, instructor_request: InstructorRequest
    ) -> tuple[InstructorRequest, User]:
        user = self.auth_repo.get_user(instructor_request.user_id)
        if user is None:
            raise RuntimeError(
                f"Instructor request {instructor_request.id} has no user"
            )
        return instructor_request, user
