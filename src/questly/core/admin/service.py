"""Admin use cases (ADR-0007 §8). Every public method takes the Actor first."""

from dataclasses import replace

from questly.core.admin.models import (
    AISettings,
    AISettingsChange,
    AISettingsWithUsage,
    ModelNotAllowedError,
    SelfModificationError,
    SystemStatus,
    UserNotFoundError,
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
        admin_repo: AdminRepository,
        auth_repo: AuthRepository,
        health_checker: SystemHealthChecker,
        allowed_models: tuple[str, ...],
    ) -> None:
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
        """Raises InstructorRequestNotFoundError or ...AlreadyReviewedError."""
        self._require_admin(actor)
        request = self.auth_repo.review_instructor_request(
            request_id=request_id, reviewer_id=actor.user_id, approve=True
        )
        return self._request_and_user(request)

    def reject_instructor_request(
        self, actor: Actor, request_id: int
    ) -> tuple[InstructorRequest, User]:
        """Raises InstructorRequestNotFoundError or ...AlreadyReviewedError."""
        self._require_admin(actor)
        request = self.auth_repo.review_instructor_request(
            request_id=request_id, reviewer_id=actor.user_id, approve=False
        )
        return self._request_and_user(request)

    # --- User Management ---
    def list_users(
        self,
        actor: Actor,
        q: str | None = None,
        role: Role | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[User], int]:
        self._require_admin(actor)
        role_value = None
        if role is not None:
            role_value = role.value
        return self.auth_repo.search_users(
            q=q, role=role_value, page=page, page_size=page_size
        )

    def update_user_role(self, actor: Actor, user_id: int, new_role: Role) -> User:
        self._require_admin(actor)
        if user_id == actor.user_id and new_role is not Role.ADMIN:
            raise SelfModificationError("Cannot demote your own admin role")
        user = self._get_user(user_id)
        return self.auth_repo.update_user(replace(user, role=new_role))

    def deactivate_user(self, actor: Actor, user_id: int) -> User:
        self._require_admin(actor)
        if user_id == actor.user_id:
            raise SelfModificationError("Cannot deactivate your own admin account")
        user = self._get_user(user_id)
        deactivated = self.auth_repo.update_user(replace(user, is_active=False))
        self.auth_repo.revoke_sessions_of(user_id)
        return deactivated

    # --- AI Settings ---
    def get_ai_settings(self, actor: Actor) -> AISettingsWithUsage:
        self._require_admin(actor)
        return self._with_usage(self.admin_repo.get_ai_settings())

    def update_ai_settings(
        self, actor: Actor, change: AISettingsChange
    ) -> AISettingsWithUsage:
        self._require_admin(actor)
        if change.model is not None and change.model not in self.allowed_models:
            raise ModelNotAllowedError(change.model)
        current = self.admin_repo.get_ai_settings()
        saved = self.admin_repo.update_ai_settings(_merge(current, change))
        return self._with_usage(saved)

    # --- System Status ---
    def get_system_status(self, actor: Actor) -> SystemStatus:
        self._require_admin(actor)
        return self.health_checker.check_services_health()

    def _with_usage(self, settings: AISettings) -> AISettingsWithUsage:
        return AISettingsWithUsage(
            settings=settings,
            usage_this_month=self.admin_repo.get_usage_this_month(),
        )

    def _require_admin(self, actor: Actor) -> None:
        if actor.role is not Role.ADMIN:
            raise PermissionDeniedError

    def _get_user(self, user_id: int) -> User:
        user = self.auth_repo.get_user(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    def _request_and_user(
        self, instructor_request: InstructorRequest
    ) -> tuple[InstructorRequest, User]:
        user = self.auth_repo.get_user(instructor_request.user_id)
        if user is None:
            raise RuntimeError(
                f"Instructor request {instructor_request.id} has no user"
            )
        return instructor_request, user


def _merge(current: AISettings, change: AISettingsChange) -> AISettings:
    """Apply the fields an Admin changed on top of the stored settings."""
    merged = current
    if change.model is not None:
        merged = replace(merged, model=change.model)
    if change.daily_quota is not None:
        merged = replace(merged, daily_quota=change.daily_quota)
    if change.max_pages is not None:
        merged = replace(merged, max_pages=change.max_pages)
    if change.require_citations is not None:
        merged = replace(merged, require_citations=change.require_citations)
    return merged
