"""Ports the submissions slice depends on."""

from collections.abc import Sequence
from typing import Protocol

from questly.core.assignments.models import (
    Assignment,
    AssignmentVersion,
    InstructorProblem,
    StudentProblem,
)
from questly.core.auth.models import Actor
from questly.core.classrooms.models import MemberView
from questly.core.submissions.models import Execution, Submission


class CodeRunner(Protocol):
    """Runs a program synchronously (Judge0 CE in prod).

    Both methods raise RunnerUnavailableError when the code could not be
    judged at all.
    """

    def run(
        self, *, code: str, language: str, stdin: str, time_limit_seconds: float
    ) -> Execution:
        """One input."""
        ...

    def run_many(
        self,
        *,
        code: str,
        language: str,
        stdins: Sequence[str],
        time_limit_seconds: float,
    ) -> tuple[Execution, ...]:
        """One batch: an Execution per input, in the order of `stdins`."""
        ...


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

    def members(self, actor: Actor, classroom_id: int) -> list[MemberView]: ...

    def is_archived(self, actor: Actor, classroom_id: int) -> bool: ...


class AssignmentLookup(Protocol):
    """Reads an Assignment's current Version number for PostingStats."""

    def get(self, assignment_id: int) -> Assignment | None: ...
