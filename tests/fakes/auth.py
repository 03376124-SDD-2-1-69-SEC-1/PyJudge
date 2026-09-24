"""In-memory AuthRepository, a settable clock, and a seeding helper."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from greader.core.auth.models import (
    InstructorRequest,
    InstructorRequestStatus,
    Role,
    Session,
    User,
    VerificationToken,
)
from greader.core.auth.service import hash_password

DEFAULT_NOW = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)


class FakeClock:
    """A clock tests move by hand."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class FakeAuthRepository:
    """Store accounts, sessions, tokens and requests in process."""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}
        self._sessions: dict[int, Session] = {}
        self._tokens: dict[int, VerificationToken] = {}
        self._requests: dict[int, InstructorRequest] = {}
        self._next_id = 1

    def _new_id(self) -> int:
        new_id = self._next_id
        self._next_id += 1
        return new_id

    def get_user(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    def find_user_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def list_users(self) -> list[User]:
        return [self._users[key] for key in sorted(self._users)]

    def create_user(self, user: User) -> User:
        created = replace(user, id=self._new_id())
        self._users[created.id] = created
        return created

    def update_user(self, user: User) -> User:
        self._users[user.id]  # KeyError for an unknown id, like the SQL adapter
        self._users[user.id] = user
        return user

    def create_session(self, session: Session) -> Session:
        created = replace(session, id=self._new_id())
        self._sessions[created.id] = created
        return created

    def find_session(self, token_hash: str) -> Session | None:
        for session in self._sessions.values():
            if session.token_hash == token_hash:
                return session
        return None

    def update_session(self, session: Session) -> Session:
        self._sessions[session.id] = session
        return session

    def revoke_sessions_of(self, user_id: int) -> None:
        for key, session in self._sessions.items():
            if session.user_id == user_id:
                self._sessions[key] = replace(session, revoked=True)

    def create_verification_token(self, token: VerificationToken) -> VerificationToken:
        created = replace(token, id=self._new_id())
        self._tokens[created.id] = created
        return created

    def find_verification_token(self, token_hash: str) -> VerificationToken | None:
        for token in self._tokens.values():
            if token.token_hash == token_hash:
                return token
        return None

    def update_verification_token(self, token: VerificationToken) -> VerificationToken:
        self._tokens[token.id] = token
        return token

    def create_instructor_request(
        self, request: InstructorRequest
    ) -> InstructorRequest:
        created = replace(request, id=self._new_id())
        self._requests[created.id] = created
        return created

    def list_instructor_requests(
        self, status: InstructorRequestStatus
    ) -> list[InstructorRequest]:
        return [
            self._requests[key]
            for key in sorted(self._requests)
            if self._requests[key].status is status
        ]

    def find_pending_instructor_request(self, user_id: int) -> InstructorRequest | None:
        for request in self._requests.values():
            if (
                request.user_id == user_id
                and request.status is InstructorRequestStatus.PENDING
            ):
                return request
        return None


# One hash reused by every seeded account: scrypt is slow on purpose, and tests
# and the demo seed create dozens of users.
DEFAULT_PASSWORD = "demo-pass-1234"
_DEFAULT_HASH = hash_password(DEFAULT_PASSWORD)


def seed_user(
    repository: FakeAuthRepository,
    *,
    email: str,
    full_name: str,
    role: Role = Role.STUDENT,
    verified: bool = True,
) -> User:
    """Insert a ready-to-log-in account whose password is DEFAULT_PASSWORD."""
    return repository.create_user(
        User(
            email=email,
            full_name=full_name,
            password_hash=_DEFAULT_HASH,
            role=role,
            email_verified=verified,
        )
    )
