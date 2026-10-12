"""AdminService rules, on the in-memory adapters."""

import pytest

from questly.core.admin.models import (
    AISettingsChange,
    ModelNotAllowedError,
    SelfModificationError,
    UserNotFoundError,
)
from questly.core.admin.service import AdminService
from questly.core.auth.models import (
    Actor,
    InstructorRequest,
    InstructorRequestAlreadyReviewedError,
    InstructorRequestNotFoundError,
    PermissionDeniedError,
    Role,
    User,
)
from tests.fakes.admin import (
    DEFAULT_AI_SETTINGS,
    FakeAdminRepository,
    FakeSystemHealthChecker,
)
from tests.fakes.auth import DEFAULT_NOW, FakeAuthRepository, seed_user


def _actor(user: User) -> Actor:
    return Actor(
        user_id=user.id, role=user.role, full_name=user.full_name, email=user.email
    )


class Admin:
    def __init__(self) -> None:
        self.auth = FakeAuthRepository()
        self.settings = FakeAdminRepository()
        self.service = AdminService(
            self.settings,
            self.auth,
            FakeSystemHealthChecker(),
            allowed_models=(DEFAULT_AI_SETTINGS.model, "other/model"),
        )
        self.admin = _actor(
            seed_user(
                self.auth, email="admin@kmitl.ac.th", full_name="Admin", role=Role.ADMIN
            )
        )
        self.student = seed_user(
            self.auth, email="66010001@kmitl.ac.th", full_name="Nattapong Suwan"
        )


def test_partial_ai_settings_change_keeps_the_other_fields() -> None:
    admin = Admin()

    updated = admin.service.update_ai_settings(
        admin.admin, AISettingsChange(daily_quota=3)
    )

    assert updated.settings.daily_quota == 3
    assert updated.settings.model == DEFAULT_AI_SETTINGS.model
    assert updated.settings.max_pages == DEFAULT_AI_SETTINGS.max_pages
    assert updated.settings.require_citations is DEFAULT_AI_SETTINGS.require_citations
    assert admin.settings.settings == updated.settings


def test_model_outside_the_allowlist_is_refused_and_nothing_is_saved() -> None:
    admin = Admin()

    with pytest.raises(ModelNotAllowedError):
        admin.service.update_ai_settings(
            admin.admin, AISettingsChange(model="unlisted/model", daily_quota=3)
        )

    assert admin.settings.settings == DEFAULT_AI_SETTINGS


def test_admin_cannot_demote_or_deactivate_themselves() -> None:
    admin = Admin()

    with pytest.raises(SelfModificationError):
        admin.service.update_user_role(admin.admin, admin.admin.user_id, Role.STUDENT)
    with pytest.raises(SelfModificationError):
        admin.service.deactivate_user(admin.admin, admin.admin.user_id)

    stored = admin.auth.get_user(admin.admin.user_id)
    assert stored.role is Role.ADMIN
    assert stored.is_active is True


def test_unknown_user_raises_user_not_found() -> None:
    admin = Admin()

    with pytest.raises(UserNotFoundError):
        admin.service.update_user_role(admin.admin, 999_999, Role.INSTRUCTOR)
    with pytest.raises(UserNotFoundError):
        admin.service.deactivate_user(admin.admin, 999_999)


def test_review_errors_come_from_the_auth_repository() -> None:
    admin = Admin()
    request = admin.auth.create_instructor_request(
        InstructorRequest(admin.student.id, "Engineering", DEFAULT_NOW)
    )
    admin.service.reject_instructor_request(admin.admin, request.id)

    with pytest.raises(InstructorRequestAlreadyReviewedError):
        admin.service.approve_instructor_request(admin.admin, request.id)
    with pytest.raises(InstructorRequestNotFoundError):
        admin.service.approve_instructor_request(admin.admin, 999_999)
    assert admin.auth.get_user(admin.student.id).role is Role.STUDENT


def test_only_an_admin_may_change_ai_settings() -> None:
    admin = Admin()

    with pytest.raises(PermissionDeniedError):
        admin.service.update_ai_settings(
            _actor(admin.student), AISettingsChange(daily_quota=1)
        )

    assert admin.settings.settings == DEFAULT_AI_SETTINGS
