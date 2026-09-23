"""Ports the classrooms slice needs.

`tests/fakes/classrooms.py` provides the in-memory ClassroomRepository and
ClassroomStats; the SQL adapter arrives with OPS-15. main.py fills
UserDirectory with AuthService, and ClassroomStats with the assignments and
submissions slices once they exist.
"""

from datetime import datetime
from typing import Protocol

from greader.core.auth.models import UserSummary
from greader.core.classrooms.models import (
    Classroom,
    InstructorCardStats,
    Membership,
    StudentCardStats,
    StudentProgress,
)


class ClassroomRepository(Protocol):
    """Classrooms and their Memberships. Each `create`/`add` assigns the id."""

    def get(self, classroom_id: int) -> Classroom | None: ...

    def list_owned_by(self, instructor_id: int) -> list[Classroom]: ...

    def list_joined_by(self, student_id: int) -> list[Classroom]: ...

    def find_by_join_code(self, join_code: str) -> Classroom | None: ...

    def create(self, classroom: Classroom) -> Classroom: ...

    def update(self, classroom: Classroom) -> Classroom: ...

    def get_membership(
        self, classroom_id: int, student_id: int
    ) -> Membership | None: ...

    def list_memberships(self, classroom_id: int) -> list[Membership]: ...

    def add_membership(self, membership: Membership) -> Membership: ...

    def remove_membership(self, classroom_id: int, student_id: int) -> bool: ...


class UserDirectory(Protocol):
    """Names and emails of accounts, for cards and the Members tab."""

    def summaries(self, user_ids: list[int]) -> list[UserSummary]: ...


class ClassroomStats(Protocol):
    """Numbers owned by other slices, shown on C-01 cards."""

    def instructor_card(self, classroom_id: int) -> InstructorCardStats: ...

    def student_card(self, classroom_id: int, student_id: int) -> StudentCardStats: ...

    def student_progress(
        self, student_id: int, classroom_ids: list[int]
    ) -> StudentProgress: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
