"""Account domain model.

No FastAPI or database imports. `Actor` and the two authorization errors are
shared by every classroom slice: a use case takes an Actor and raises
PermissionDeniedError; the handler maps it to 403.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Role(StrEnum):
    """Global account role. Every account starts as a Student."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class Landing(StrEnum):
    """Where an account lands after logging in."""

    CLASSROOMS = "classrooms"
    ADMIN_SETTINGS = "admin_settings"


class InstructorRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class NotAuthenticatedError(Exception):
    """No valid session: pages redirect to /login, the API answers 401."""


class PermissionDeniedError(Exception):
    """The Actor is known but may not do this: 403."""


class CsrfTokenError(Exception):
    """A form post without the token its page was rendered with: 403."""


@dataclass(frozen=True, slots=True)
class User:
    """An account. `id` is `None` only before the repository persisted it."""

    email: str
    full_name: str
    password_hash: str
    role: Role = Role.STUDENT
    email_verified: bool = False
    is_active: bool = True
    last_active_at: datetime | None = None
    id: int | None = None

    @property
    def student_number(self) -> str | None:
        """KMITL student ID: the email's local part when it is all digits."""
        local_part = self.email.split("@", 1)[0]
        if local_part.isdigit():
            return local_part
        return None


@dataclass(frozen=True, slots=True)
class Actor:
    """The logged-in account a use case runs for."""

    user_id: int
    role: Role
    full_name: str
    email: str

    @property
    def owns_classrooms(self) -> bool:
        """Whether this account sees Instructor navigation (My documents)."""
        return self.role is Role.INSTRUCTOR


@dataclass(frozen=True, slots=True)
class UserSummary:
    """What other slices may know about an account: name and contact only."""

    user_id: int
    full_name: str
    email: str

    @property
    def student_number(self) -> str | None:
        local_part = self.email.split("@", 1)[0]
        if local_part.isdigit():
            return local_part
        return None


@dataclass(frozen=True, slots=True)
class Session:
    """A login. Only the SHA-256 of the cookie token is stored.

    `csrf_token` is the synchronizer token every form posted during this
    session must echo back; it is minted with the session and dies with it.
    """

    token_hash: str
    user_id: int
    expires_at: datetime
    csrf_token: str
    revoked: bool = False
    id: int | None = None


@dataclass(frozen=True, slots=True)
class VerificationToken:
    """A one-time email verification link, valid for 24 hours."""

    token_hash: str
    user_id: int
    expires_at: datetime
    used: bool = False
    id: int | None = None


@dataclass(frozen=True, slots=True)
class InstructorRequest:
    """A Student's application to become an Instructor, reviewed by an Admin."""

    user_id: int
    faculty: str
    requested_at: datetime
    status: InstructorRequestStatus = InstructorRequestStatus.PENDING
    id: int | None = None


@dataclass(frozen=True, slots=True)
class LoginResult:
    """A new session token (for the cookie) and where the account lands."""

    token: str
    user: User
    landing: Landing
