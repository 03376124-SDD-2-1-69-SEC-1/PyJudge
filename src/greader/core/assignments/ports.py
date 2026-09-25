"""Ports the assignments slice needs.

`tests/fakes/assignments.py` provides in-memory adapters for all three
repositories and PostingStats. Production wires `database/pending.py` for
them until OPS-15 (ADR-0007 §10.4); `database/core/assignment_repository.py`
still implements the old AssignmentRepository shape and is not wired.
main.py fills ClassroomAccess with ClassroomService, and PostingStats with the
submissions slice once it exists.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from greader.core.assignments.models import (
    Assignment,
    AssignmentVersion,
    Posting,
    PostingSummary,
    StudentStanding,
)
from greader.core.auth.models import Actor
from greader.core.classrooms.models import ClassroomRole


class AssignmentRepository(Protocol):
    """The current content of Assignments.

    `create` and `update` are the only operations allowed to assign an id, for
    the Assignment and its test cases alike. Callers use the returned object.
    """

    def list(self) -> list[Assignment]: ...

    def get(self, assignment_id: int) -> Assignment | None: ...

    def create(self, assignment: Assignment) -> Assignment: ...

    def update(self, assignment: Assignment) -> Assignment: ...

    def delete(self, assignment_id: int) -> bool: ...


class VersionRepository(Protocol):
    """Append-only history of Assignment content."""

    def append(self, version: AssignmentVersion) -> AssignmentVersion: ...

    def list_for(self, assignment_id: int) -> list[AssignmentVersion]: ...

    def get(self, assignment_id: int, number: int) -> AssignmentVersion | None: ...


class PostingRepository(Protocol):
    """Postings. `create` is the only operation that assigns an id."""

    def create(self, posting: Posting) -> Posting: ...

    def update(self, posting: Posting) -> Posting: ...

    def delete(self, posting_id: int) -> bool: ...

    def find(self, classroom_id: int, assignment_id: int) -> Posting | None: ...

    def list_for_classroom(self, classroom_id: int) -> list[Posting]: ...

    def list_for_assignment(self, assignment_id: int) -> list[Posting]: ...


class ClassroomAccess(Protocol):
    """What the classrooms slice knows: roles, member counts and names."""

    def role_of(self, actor: Actor, classroom_id: int) -> ClassroomRole: ...

    def member_ids(self, actor: Actor, classroom_id: int) -> list[int]: ...

    def member_names(
        self, actor: Actor, classroom_id: int
    ) -> list[tuple[int, str]]: ...


class PostingStats(Protocol):
    """Numbers derived from Submissions, owned by the submissions slice."""

    def posting_summary(self, posting_id: int) -> PostingSummary: ...

    def standing(self, posting_id: int, student_id: int) -> StudentStanding: ...

    def score(self, posting_id: int, student_id: int) -> float | None: ...

    def fail_rate(self, posting_id: int) -> float | None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
