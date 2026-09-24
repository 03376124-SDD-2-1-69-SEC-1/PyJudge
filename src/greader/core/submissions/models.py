"""Submission and Run domain model (ADR-0007 §5).

A Submission is graded against every Test Case of a Posting and always kept;
a Run executes the sample Test Cases only and is never kept. No FastAPI,
ORM or runner client imports here.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from greader.core.assignments.models import (
    AssignmentVersion,
    InstructorProblem,
    StudentProblem,
    TestCase,
    TestCaseKind,
)


class Verdict(StrEnum):
    PASSED = "passed"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT = "time_limit"
    RUNTIME_ERROR = "runtime_error"


class ExecutionStatus(StrEnum):
    OK = "ok"
    TIME_LIMIT = "time_limit"
    RUNTIME_ERROR = "runtime_error"


@dataclass(frozen=True, slots=True)
class Execution:
    """What the CodeRunner reports for one program run on one input."""

    status: ExecutionStatus
    stdout: str
    stderr: str
    time_seconds: float


@dataclass(frozen=True, slots=True)
class TestResult:
    """One Test Case's outcome.

    `position` is the Test Case's 1-based place in the Version, `ordinal`
    its 1-based place among Test Cases of the same kind ("Hidden 2").
    `actual_output` and `error` are kept for every test; the page decides
    what a Student may see.
    """

    position: int
    ordinal: int
    kind: TestCaseKind
    note: str
    verdict: Verdict
    time_seconds: float
    expected_output: str
    actual_output: str
    error: str

    @property
    def passed(self) -> bool:
        return self.verdict is Verdict.PASSED


@dataclass(frozen=True, slots=True)
class Submission:
    """A Student's graded code for one Posting. `id` is `None` before save."""

    posting_id: int
    classroom_id: int
    assignment_id: int
    student_id: int
    version_number: int
    code: str
    language: str
    submitted_at: datetime
    is_late: bool
    score: int
    max_score: int
    attempt: int
    results: tuple[TestResult, ...] = field(default_factory=tuple)
    id: int | None = None

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def all_passed(self) -> bool:
        return self.passed_count == len(self.results)

    @property
    def failed(self) -> tuple[TestResult, ...]:
        return tuple(result for result in self.results if not result.passed)


@dataclass(frozen=True, slots=True)
class RunReport:
    """An ungraded Run on the sample Test Cases; never stored."""

    code: str
    results: tuple[TestResult, ...]

    @property
    def time_seconds(self) -> float:
        return sum(result.time_seconds for result in self.results)


class StudentTab(StrEnum):
    PROBLEM = "problem"
    HISTORY = "history"


class InstructorTab(StrEnum):
    RESULTS = "results"
    VERSIONS = "versions"


@dataclass(frozen=True, slots=True)
class StudentSolveView:
    """S-02 for a Member: the problem, their Submissions and what they may do.

    `counted` is the latest Submission, or None before the first one.
    `update` is the current Version when the counted Submission is on an
    older one (S-02e), else None.
    """

    problem: StudentProblem
    samples: tuple[TestCase, ...]
    hidden_count: int
    submissions: tuple[Submission, ...]
    counted: Submission | None
    update: AssignmentVersion | None
    closed: bool
    archived: bool
    can_submit: bool


@dataclass(frozen=True, slots=True)
class TestFailure:
    """T-02 "Failing": share of Counted Submissions failing one Test Case."""

    position: int
    ordinal: int
    kind: TestCaseKind
    note: str
    rate: float | None


@dataclass(frozen=True, slots=True)
class StudentResult:
    """One Member's row on T-02; `counted` is None if they never submitted."""

    student_id: int
    name: str
    counted: Submission | None
    attempts: int


@dataclass(frozen=True, slots=True)
class InstructorResultsView:
    """T-02 for the owning Instructor."""

    problem: InstructorProblem
    rows: tuple[StudentResult, ...]
    failures: tuple[TestFailure, ...]
    versions: tuple[AssignmentVersion, ...]
    closed: bool

    @property
    def submitted(self) -> tuple[StudentResult, ...]:
        return tuple(row for row in self.rows if row.counted is not None)

    @property
    def average_score(self) -> float | None:
        scores = [row.counted.score for row in self.submitted if row.counted]
        if not scores:
            return None
        return sum(scores) / len(scores)

    @property
    def all_passed(self) -> int:
        return sum(
            1 for row in self.submitted if row.counted and row.counted.all_passed
        )

    @property
    def late(self) -> int:
        return sum(1 for row in self.submitted if row.counted and row.counted.is_late)


class SubmissionNotFoundError(LookupError):
    pass


class PostingClosedError(Exception):
    """The Posting accepts no more Submissions or Runs."""


class ClassroomArchivedError(PostingClosedError):
    """An Archived Classroom takes no Submissions or Runs (ADR-0007 §2)."""


class ResubmissionNotAllowedError(Exception):
    """The Posting allows one Submit only and the Student has used it."""


class EmptyCodeError(ValueError):
    pass
