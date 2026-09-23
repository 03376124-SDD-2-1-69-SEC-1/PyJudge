"""Ports the auth slice needs.

`tests/fakes/auth.py` provides the in-memory AuthRepository; the SQL adapter
arrives with OPS-15. main.py fills VerificationMailer with the email stub
until the notifications slice owns sending (ADR-0007 §6.4) — swapping it
changes only main.py.
"""

from datetime import datetime
from typing import Protocol

from greader.core.auth.models import (
    InstructorRequest,
    InstructorRequestStatus,
    Session,
    User,
    VerificationToken,
)


class AuthRepository(Protocol):
    """Accounts, sessions, verification tokens and Instructor requests.

    Each `create_*` is the only operation that assigns an id.
    """

    def get_user(self, user_id: int) -> User | None: ...

    def find_user_by_email(self, email: str) -> User | None: ...

    def list_users(self) -> list[User]: ...

    def create_user(self, user: User) -> User: ...

    def update_user(self, user: User) -> User: ...

    def create_session(self, session: Session) -> Session: ...

    def find_session(self, token_hash: str) -> Session | None: ...

    def update_session(self, session: Session) -> Session: ...

    def revoke_sessions_of(self, user_id: int) -> None: ...

    def create_verification_token(
        self, token: VerificationToken
    ) -> VerificationToken: ...

    def find_verification_token(self, token_hash: str) -> VerificationToken | None: ...

    def update_verification_token(
        self, token: VerificationToken
    ) -> VerificationToken: ...

    def create_instructor_request(
        self, request: InstructorRequest
    ) -> InstructorRequest: ...

    def list_instructor_requests(
        self, status: InstructorRequestStatus
    ) -> list[InstructorRequest]: ...

    def find_pending_instructor_request(
        self, user_id: int
    ) -> InstructorRequest | None: ...


class VerificationMailer(Protocol):
    """Sends the email verification link."""

    def send_verification(
        self, *, email: str, full_name: str, verify_path: str
    ) -> None:
        """Deliver `verify_path` (e.g. `/verify?token=...`) to `email`."""
        ...


class Clock(Protocol):
    """The current time, timezone-aware UTC. Injected so expiry is testable."""

    def now(self) -> datetime: ...
