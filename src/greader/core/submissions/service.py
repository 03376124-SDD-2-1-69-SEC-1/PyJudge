"""Submission and Run use cases (ADR-0007 §5) and the T-02 numbers (§7)."""

from datetime import datetime

from greader.core.assignments.models import (
    Assignment,
    InstructorProblem,
    StudentProblem,
    TestCase,
    TestCaseKind,
)
from greader.core.assignments.ports import Clock
from greader.core.assignments.service import (
    AssignmentNotFoundError,
    ClassroomNotVisibleError,
    PostingNotFoundError,
)
from greader.core.auth.models import Actor, PermissionDeniedError
from greader.core.submissions.models import (
    ClassroomArchivedError,
    EmptyCodeError,
    Execution,
    ExecutionStatus,
    InstructorResultsView,
    PostingClosedError,
    ResubmissionNotAllowedError,
    RunReport,
    StudentResult,
    StudentSolveView,
    Submission,
    SubmissionNotFoundError,
    TestFailure,
    TestResult,
    Verdict,
)
from greader.core.submissions.ports import (
    CodeRunner,
    Problems,
    Roster,
    SubmissionRepository,
)


def outputs_match(expected: str, actual: str) -> bool:
    """Equal after dropping trailing spaces on each line and trailing blank lines."""

    def normalise(text: str) -> list[str]:
        return [line.rstrip() for line in text.rstrip().splitlines()]

    return normalise(expected) == normalise(actual)


def judge(test_case: TestCase, execution: Execution) -> Verdict:
    if execution.status is ExecutionStatus.TIME_LIMIT:
        return Verdict.TIME_LIMIT
    if execution.status is ExecutionStatus.RUNTIME_ERROR:
        return Verdict.RUNTIME_ERROR
    if outputs_match(test_case.expected_output, execution.stdout):
        return Verdict.PASSED
    return Verdict.WRONG_ANSWER


def score_for(results: tuple[TestResult, ...], max_score: int) -> int:
    """Share of passed tests times max score, rounded down; no tests scores 0."""
    if not results:
        return 0
    passed = sum(1 for result in results if result.passed)
    return max_score * passed // len(results)


def ordinals(test_cases: list[TestCase]) -> list[int]:
    """1-based place of each Test Case among those of its kind ("Hidden 2")."""
    seen: dict[TestCaseKind, int] = {}
    places = []
    for test_case in test_cases:
        seen[test_case.kind] = seen.get(test_case.kind, 0) + 1
        places.append(seen[test_case.kind])
    return places


# What a page or route answers with 404: the Posting is not there for the Actor.
NOT_VISIBLE = (
    AssignmentNotFoundError,
    ClassroomNotVisibleError,
    PostingNotFoundError,
    SubmissionNotFoundError,
)


class SubmissionService:
    def __init__(
        self,
        repository: SubmissionRepository,
        runner: CodeRunner,
        problems: Problems,
        roster: Roster,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._problems = problems
        self._roster = roster
        self._clock = clock

    # ---- Pages --------------------------------------------------------------

    def page(
        self, actor: Actor, classroom_id: int, assignment_id: int
    ) -> StudentSolveView | InstructorResultsView:
        """S-02 for a Member, T-02 for the owning Instructor."""
        problem = self._problems.problem(actor, classroom_id, assignment_id)
        if isinstance(problem, InstructorProblem):
            return self._results(actor, classroom_id, problem)
        return self._solve(actor, classroom_id, problem)

    def submissions(
        self, actor: Actor, classroom_id: int, assignment_id: int
    ) -> tuple[Submission, ...]:
        """Every Student's for the owner; a Member's own (S-02g). Oldest first."""
        problem = self._problems.problem(actor, classroom_id, assignment_id)
        if isinstance(problem, InstructorProblem):
            return self._repository.list_for_posting(problem.posting.id)
        return self._repository.list_for_student(problem.posting.id, actor.user_id)

    def get(self, actor: Actor, submission_id: int) -> Submission:
        """A Student's own Submission, or any on the Instructor's Posting."""
        submission = self._repository.get(submission_id)
        if submission is None:
            raise SubmissionNotFoundError
        if submission.student_id == actor.user_id:
            return submission
        try:
            problem = self._problems.problem(
                actor, submission.classroom_id, submission.assignment_id
            )
        except NOT_VISIBLE:
            raise SubmissionNotFoundError from None
        if not isinstance(problem, InstructorProblem):
            raise SubmissionNotFoundError
        return submission

    # ---- Run and Submit -----------------------------------------------------

    def run(
        self, actor: Actor, classroom_id: int, assignment_id: int, code: str
    ) -> RunReport:
        """Sample Test Cases only; not graded, not stored (ADR-0007 §5.3)."""
        problem = self._student_problem(actor, classroom_id, assignment_id)
        self._require_open(actor, problem)
        self._require_code(code)
        samples = [
            test_case
            for test_case in problem.assignment.test_cases
            if test_case.kind is TestCaseKind.SAMPLE
        ]
        return RunReport(
            code=code, results=self._execute(problem.assignment, samples, code)
        )

    def submit(
        self, actor: Actor, classroom_id: int, assignment_id: int, code: str
    ) -> Submission:
        """Grade against every Test Case and keep it; the latest one counts."""
        problem = self._student_problem(actor, classroom_id, assignment_id)
        self._require_open(actor, problem)
        self._require_code(code)
        posting = problem.posting
        previous = self._repository.list_for_student(posting.id, actor.user_id)
        if previous and not posting.schedule.allow_resubmission:
            raise ResubmissionNotAllowedError
        assignment = problem.assignment
        results = self._execute(assignment, assignment.test_cases, code)
        now = self._clock.now()
        return self._repository.add(
            Submission(
                posting_id=posting.id,
                classroom_id=classroom_id,
                assignment_id=assignment.id,
                student_id=actor.user_id,
                version_number=assignment.current_version,
                code=code,
                language=assignment.settings.language.value,
                submitted_at=now,
                is_late=now > posting.schedule.deadline,
                score=score_for(results, posting.schedule.max_score),
                max_score=posting.schedule.max_score,
                attempt=len(previous) + 1,
                results=results,
            )
        )

    # ---- Internals ----------------------------------------------------------

    def _student_problem(
        self, actor: Actor, classroom_id: int, assignment_id: int
    ) -> StudentProblem:
        problem = self._problems.problem(actor, classroom_id, assignment_id)
        if not isinstance(problem, StudentProblem):
            raise PermissionDeniedError
        return problem

    def _require_open(self, actor: Actor, problem: StudentProblem) -> None:
        if self._roster.is_archived(actor, problem.posting.classroom_id):
            raise ClassroomArchivedError
        if problem.posting.is_closed(self._clock.now()):
            raise PostingClosedError

    @staticmethod
    def _require_code(code: str) -> None:
        if not code.strip():
            raise EmptyCodeError

    def _execute(
        self, assignment: Assignment, test_cases: list[TestCase], code: str
    ) -> tuple[TestResult, ...]:
        settings = assignment.settings
        results = []
        for position, (test_case, ordinal) in enumerate(
            zip(test_cases, ordinals(test_cases), strict=True), start=1
        ):
            execution = self._runner.run(
                code=code,
                language=settings.language.value,
                stdin=test_case.input_data,
                time_limit_seconds=settings.time_limit_ms / 1000,
            )
            results.append(
                TestResult(
                    position=position,
                    ordinal=ordinal,
                    kind=test_case.kind,
                    note=test_case.note,
                    verdict=judge(test_case, execution),
                    time_seconds=execution.time_seconds,
                    expected_output=test_case.expected_output,
                    actual_output=execution.stdout,
                    error=execution.stderr,
                )
            )
        return tuple(results)

    def _solve(
        self, actor: Actor, classroom_id: int, problem: StudentProblem
    ) -> StudentSolveView:
        posting = problem.posting
        assignment = problem.assignment
        submissions = self._repository.list_for_student(posting.id, actor.user_id)
        counted = submissions[-1] if submissions else None
        update = None
        if counted is not None and counted.version_number < assignment.current_version:
            update = self._problems.current_version(actor, classroom_id, assignment.id)
        archived = self._roster.is_archived(actor, classroom_id)
        closed = archived or posting.is_closed(self._clock.now())
        samples = tuple(
            test_case
            for test_case in assignment.test_cases
            if test_case.kind is TestCaseKind.SAMPLE
        )
        return StudentSolveView(
            problem=problem,
            samples=samples,
            hidden_count=len(assignment.test_cases) - len(samples),
            submissions=submissions,
            counted=counted,
            update=update,
            closed=closed,
            archived=archived,
            can_submit=not closed
            and (posting.schedule.allow_resubmission or not submissions),
        )

    def _results(
        self, actor: Actor, classroom_id: int, problem: InstructorProblem
    ) -> InstructorResultsView:
        by_student: dict[int, list[Submission]] = {}
        for submission in self._repository.list_for_posting(problem.posting.id):
            by_student.setdefault(submission.student_id, []).append(submission)
        rows = tuple(
            StudentResult(
                student_id=student_id,
                name=name,
                counted=by_student[student_id][-1]
                if student_id in by_student
                else None,
                attempts=len(by_student.get(student_id, [])),
            )
            for student_id, name in self._roster.member_names(actor, classroom_id)
        )
        counted = [row.counted for row in rows if row.counted is not None]
        test_cases = problem.assignment.test_cases
        failures = tuple(
            TestFailure(
                position=position,
                ordinal=ordinal,
                kind=test_case.kind,
                note=test_case.note,
                rate=_failing_share(counted, position),
            )
            for position, (test_case, ordinal) in enumerate(
                zip(test_cases, ordinals(test_cases), strict=True), start=1
            )
        )
        return InstructorResultsView(
            problem=problem,
            rows=rows,
            failures=failures,
            versions=tuple(self._problems.versions(actor, problem.assignment.id)),
            closed=problem.posting.is_closed(self._clock.now()),
        )


def _failing_share(counted: list[Submission], position: int) -> float | None:
    """Share of Counted Submissions that ran this test and failed it."""
    ran = [
        result
        for submission in counted
        for result in submission.results
        if result.position == position
    ]
    if not ran:
        return None
    return sum(1 for result in ran if not result.passed) / len(ran)


def counted_submissions(
    submissions: tuple[Submission, ...],
) -> tuple[Submission, ...]:
    """Each Student's Counted Submission: their latest one."""
    latest: dict[int, Submission] = {}
    for submission in sorted(submissions, key=_submitted_order):
        latest[submission.student_id] = submission
    return tuple(latest.values())


def _submitted_order(submission: Submission) -> tuple[datetime, int]:
    return (submission.submitted_at, submission.attempt)
