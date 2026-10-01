"""Contract every AuthRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/auth/` and to
`SQLAuthRepository` in `tests/db/`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from questly.core.auth.models import (
    InstructorRequest,
    InstructorRequestStatus,
    Role,
    Session,
    User,
    VerificationToken,
)
from questly.core.auth.ports import AuthRepository

NOW = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)


def user(email: str = "65010001@kmitl.ac.th", **changes: object) -> User:
    """A not-yet-persisted account; override any field by keyword."""
    base = User(email=email, full_name="Somchai Jaidee", password_hash="scrypt$x")
    return replace(base, **changes)


class AuthRepositoryContract:
    """Checks that hold for any store behind AuthRepository."""

    # ---- users -------------------------------------------------------------

    def test_create_user_assigns_an_int_id(self, repository: AuthRepository) -> None:
        created = repository.create_user(user())

        assert isinstance(created.id, int)

    def test_create_user_round_trips_every_field(
        self, repository: AuthRepository
    ) -> None:
        created = repository.create_user(
            user(
                role=Role.INSTRUCTOR,
                email_verified=True,
                is_active=False,
                last_active_at=NOW,
            )
        )

        assert repository.get_user(created.id) == created
        assert created.role is Role.INSTRUCTOR
        assert created.email_verified is True
        assert created.is_active is False
        assert created.last_active_at == NOW

    def test_get_user_on_unknown_id_returns_none(
        self, repository: AuthRepository
    ) -> None:
        assert repository.get_user(999_999) is None

    def test_find_user_by_email_matches_exactly(
        self, repository: AuthRepository
    ) -> None:
        created = repository.create_user(user("a@kmitl.ac.th"))

        assert repository.find_user_by_email("a@kmitl.ac.th") == created
        assert repository.find_user_by_email("b@kmitl.ac.th") is None

    def test_list_users_is_ordered_by_id(self, repository: AuthRepository) -> None:
        first = repository.create_user(user("a@kmitl.ac.th"))
        second = repository.create_user(user("b@kmitl.ac.th"))

        assert repository.list_users() == [first, second]

    def test_update_user_replaces_stored_values(
        self, repository: AuthRepository
    ) -> None:
        created = repository.create_user(user())
        changed = replace(
            created,
            full_name="Somchai J.",
            role=Role.ADMIN,
            email_verified=True,
            last_active_at=NOW,
        )

        assert repository.update_user(changed) == changed
        assert repository.get_user(created.id) == changed

    def test_update_user_can_clear_verification(
        self, repository: AuthRepository
    ) -> None:
        created = repository.create_user(user(email_verified=True))

        repository.update_user(replace(created, email_verified=False))

        assert repository.get_user(created.id).email_verified is False

    def test_update_user_on_unknown_id_raises_key_error(
        self, repository: AuthRepository
    ) -> None:
        with pytest.raises(KeyError):
            repository.update_user(user(id=999_999))

    # ---- sessions ----------------------------------------------------------

    def test_create_and_find_session_by_token_hash(
        self, repository: AuthRepository
    ) -> None:
        owner = repository.create_user(user())
        created = repository.create_session(
            Session(
                token_hash="h1",
                user_id=owner.id,
                expires_at=NOW + timedelta(days=7),
                csrf_token="csrf-1",
            )
        )

        assert isinstance(created.id, int)
        assert repository.find_session("h1") == created
        assert repository.find_session("nope") is None

    def test_update_session_persists_revocation(
        self, repository: AuthRepository
    ) -> None:
        owner = repository.create_user(user())
        created = repository.create_session(
            Session("h1", owner.id, NOW + timedelta(days=7), "csrf-1")
        )

        revoked = repository.update_session(replace(created, revoked=True))

        assert revoked.revoked is True
        assert repository.find_session("h1") == revoked

    def test_revoke_sessions_of_touches_only_that_user(
        self, repository: AuthRepository
    ) -> None:
        alice = repository.create_user(user("a@kmitl.ac.th"))
        bob = repository.create_user(user("b@kmitl.ac.th"))
        expiry = NOW + timedelta(days=7)
        repository.create_session(Session("a1", alice.id, expiry, "c"))
        repository.create_session(Session("a2", alice.id, expiry, "c"))
        repository.create_session(Session("b1", bob.id, expiry, "c"))

        repository.revoke_sessions_of(alice.id)

        assert repository.find_session("a1").revoked is True
        assert repository.find_session("a2").revoked is True
        assert repository.find_session("b1").revoked is False

    # ---- verification tokens -----------------------------------------------

    def test_verification_token_round_trip_and_use(
        self, repository: AuthRepository
    ) -> None:
        owner = repository.create_user(user())
        created = repository.create_verification_token(
            VerificationToken("t1", owner.id, NOW + timedelta(hours=24))
        )

        assert isinstance(created.id, int)
        assert repository.find_verification_token("t1") == created
        assert repository.find_verification_token("t2") is None

        used = repository.update_verification_token(replace(created, used=True))

        assert repository.find_verification_token("t1") == used
        assert used.used is True

    # ---- instructor requests -----------------------------------------------

    def test_instructor_requests_filter_by_status_in_id_order(
        self, repository: AuthRepository
    ) -> None:
        alice = repository.create_user(user("a@kmitl.ac.th"))
        bob = repository.create_user(user("b@kmitl.ac.th"))
        first = repository.create_instructor_request(
            InstructorRequest(alice.id, "Engineering", NOW)
        )
        second = repository.create_instructor_request(
            InstructorRequest(bob.id, "Science", NOW + timedelta(minutes=1))
        )

        assert isinstance(first.id, int)
        assert repository.list_instructor_requests(InstructorRequestStatus.PENDING) == [
            first,
            second,
        ]
        assert (
            repository.list_instructor_requests(InstructorRequestStatus.APPROVED) == []
        )

    def test_find_pending_instructor_request(self, repository: AuthRepository) -> None:
        alice = repository.create_user(user("a@kmitl.ac.th"))
        bob = repository.create_user(user("b@kmitl.ac.th"))
        pending = repository.create_instructor_request(
            InstructorRequest(alice.id, "Engineering", NOW)
        )
        repository.create_instructor_request(
            InstructorRequest(
                bob.id, "Science", NOW, status=InstructorRequestStatus.REJECTED
            )
        )

        assert repository.find_pending_instructor_request(alice.id) == pending
        assert repository.find_pending_instructor_request(bob.id) is None
