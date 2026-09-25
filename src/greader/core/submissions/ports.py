"""Ports the submissions slice depends on."""

from typing import Protocol

from greader.core.assignments.models import (
    Assignment,
    AssignmentVersion,
    InstructorProblem,
    StudentProblem,
)
from greader.core.auth.models import Actor
from greader.core.submissions.models import Execution, Submission


class CodeRunner(Protocol):
    """Runs one program on one input, synchronously (Judge0 CE in prod)."""

    def run(
        self, *, code: str, language: str, stdin: str, time_limit_seconds: float
    ) -> Execution: ...


class SubmissionRepository(Protocol):
    def add(self, submission: Submission) -> Submission: ...

    def get(self, submission_id: int) -> Submission | None: ...

    def list_for_student(
        self, posting_id: int, student_id: int
    ) -> tuple[Submission, ...]:
        """Oldest first."""
        ...

    def list_for_posting(self, posting_id: int) -> tuple[Submission, ...]:
        """Every Student's Submissions, oldest first."""
        ...


class Problems(Protocol):
    """The Postings a Submission is for; filled by AssignmentService."""

    def problem(
        self, actor: Actor, classroom_id: int, assignment_id: int
    ) -> InstructorProblem | StudentProblem: ...

    def current_version(
        self, actor: Actor, classroom_id: int, assignment_id: int
    ) -> AssignmentVersion: ...

    def versions(self, actor: Actor, assignment_id: int) -> list[AssignmentVersion]: ...


class Roster(Protocol):
    """Who a Classroom's Members are; filled by ClassroomService."""

    def member_names(
        self, actor: Actor, classroom_id: int
    ) -> list[tuple[int, str]]: ...

    def is_archived(self, actor: Actor, classroom_id: int) -> bool: ...


class AssignmentLookup(Protocol):
    """Reads an Assignment's current Version number for PostingStats."""

    def get(self, assignment_id: int) -> Assignment | None: ...
