"""SubmissionService (Run vs Submit, Late, Closed) and SubmissionPostingStats."""

from datetime import UTC, datetime, timedelta

import pytest

from greader.core.assignments.models import (
    AssignmentContent,
    Difficulty,
    Schedule,
    StudentState,
    TestCase,
    TestCaseKind,
)
from greader.core.assignments.service import (
    AssignmentService,
    ClassroomNotVisibleError,
    PostingNotFoundError,
)
from greader.core.auth.models import Actor, PermissionDeniedError, Role
from greader.core.auth.service import AuthService
from greader.core.classrooms.service import ClassroomService
from greader.core.submissions.models import (
    EmptyCodeError,
    Execution,
    ExecutionStatus,
    InstructorResultsView,
    PostingClosedError,
    ResubmissionNotAllowedError,
    StudentSolveView,
    SubmissionNotFoundError,
    Verdict,
)
from greader.core.submissions.service import (
    SubmissionService,
    judge,
    outputs_match,
    score_for,
)
from greader.core.submissions.stats import SubmissionPostingStats
from greader.integrations.email import StubEmailSender
from tests.fakes.assignments import (
    FakeAssignmentRepository,
    FakePostingRepository,
    FakeVersionRepository,
)
from tests.fakes.auth import FakeAuthRepository, FakeClock, seed_user
from tests.fakes.classrooms import FakeClassroomRepository, FakeClassroomStats
from tests.fakes.submissions import FakeSubmissionRepository, ScriptedCodeRunner

NOW = datetime(2026, 9, 24, 3, 0, tzinfo=UTC)
DEADLINE = NOW + timedelta(days=7)
TESTS = [
    TestCase(input_data="1", expected_output="one"),
    TestCase(input_data="2", expected_output="two"),
    TestCase(input_data="3", expected_output="three", kind=TestCaseKind.HIDDEN),
    TestCase(
        input_data="", expected_output="none", kind=TestCaseKind.EDGE, note="empty"
    ),
]
CORRECT = {"1": "one", "2": "two", "3": "three", "": "none"}


class World:
    def __init__(self) -> None:
        self.clock = FakeClock(NOW)
        users = FakeAuthRepository()
        auth = AuthService(users, StubEmailSender(), self.clock)
        self.classrooms = ClassroomService(
            FakeClassroomRepository(), auth, FakeClassroomStats(), self.clock
        )
        self.submissions = FakeSubmissionRepository()
        assignments = FakeAssignmentRepository()
        self.assignments = AssignmentService(
            assignments,
            FakeVersionRepository(),
            FakePostingRepository(),
            self.classrooms,
            SubmissionPostingStats(self.submissions, assignments),
            self.clock,
        )
        self.runner = ScriptedCodeRunner(CORRECT)
        self.service = SubmissionService(
            self.submissions, self.runner, self.assignments, self.classrooms, self.clock
        )

        def actor(email: str, name: str, role: Role) -> Actor:
            user = seed_user(users, email=email, full_name=name, role=role)
            return Actor(user_id=user.id, role=role, full_name=name, email=email)

        self.teacher = actor(
            "somchai.p@kmitl.ac.th", "Somchai Prasert", Role.INSTRUCTOR
        )
        self.student = actor("66010001@kmitl.ac.th", "Nattapong Suwan", Role.STUDENT)
        self.other = actor("66010002@kmitl.ac.th", "Pimchanok Wong", Role.STUDENT)
        self.outsider = actor("66010009@kmitl.ac.th", "Out Sider", Role.STUDENT)
        self.room = self.classrooms.create(
            self.teacher,
            course_code="01076001",
            course_name="Programming I",
            section="1",
            semester="1/2569",
        )
        self.classrooms.join(self.student, self.room.join_code)
        self.classrooms.join(self.other, self.room.join_code)

    def publish(self, **schedule: object) -> int:
        published = self.assignments.publish(
            self.teacher,
            AssignmentContent(
                title="Numbers to words",
                problem_statement="Print the word.",
                difficulty=Difficulty.EASY,
                test_cases=TESTS,
            ),
            Schedule(deadline=DEADLINE, **schedule),
            [self.room.id],
        )
        return published.assignment.id

    def submit(self, aid: int, code: str = "print(answer)", who: Actor | None = None):
        if who is None:
            who = self.student
        return self.service.submit(who, self.room.id, aid, code)


@pytest.fixture()
def world() -> World:
    return World()


def test_outputs_match_ignores_trailing_whitespace_only() -> None:
    assert outputs_match("1 2\n3", "1 2  \n3\n\n")
    assert not outputs_match("1 2", "1  2")


def test_judge_maps_runner_status_before_comparing() -> None:
    case = TestCase(input_data="", expected_output="x")
    assert judge(case, Execution(ExecutionStatus.OK, "x\n", "", 0)) is Verdict.PASSED
    assert judge(case, Execution(ExecutionStatus.OK, "y", "", 0)) is (
        Verdict.WRONG_ANSWER
    )
    assert judge(case, Execution(ExecutionStatus.TIME_LIMIT, "x", "", 1)) is (
        Verdict.TIME_LIMIT
    )


def test_score_rounds_down_the_passed_share(world: World) -> None:
    aid = world.publish()
    world.runner.outputs = {"1": "one", "2": "two"}

    submission = world.submit(aid)

    assert (submission.passed_count, submission.score) == (2, 5)
    assert score_for((), 10) == 0


def test_run_executes_sample_tests_only_and_keeps_nothing(world: World) -> None:
    aid = world.publish()

    report = world.service.run(world.student, world.room.id, aid, "print(x)")

    assert [r.kind for r in report.results] == [TestCaseKind.SAMPLE] * 2
    assert world.runner.calls == ["1", "2"]
    assert world.service.submissions(world.student, world.room.id, aid) == ()


def test_submit_grades_every_test_and_counts_attempts(world: World) -> None:
    aid = world.publish()

    first = world.submit(aid, "# crash")
    second = world.submit(aid)

    assert first.results[0].verdict is Verdict.RUNTIME_ERROR
    assert (first.attempt, first.score) == (1, 0)
    assert (second.attempt, second.score, second.all_passed) == (2, 10, True)
    assert second.version_number == 1 and not second.is_late


def test_latest_submission_counts_even_when_lower(world: World) -> None:
    aid = world.publish()
    world.submit(aid)
    world.submit(aid, "# tle")

    view = world.service.page(world.student, world.room.id, aid)

    assert isinstance(view, StudentSolveView)
    assert view.counted.score == 0
    assert view.counted.results[0].verdict is Verdict.TIME_LIMIT
    standing = world.assignments.problem(world.student, world.room.id, aid).standing
    assert (standing.state, standing.score) == (StudentState.PARTIAL, 0)


def test_after_the_deadline_late_work_is_flagged_not_penalised(world: World) -> None:
    aid = world.publish(allow_late=True)
    world.clock.advance(timedelta(days=8))

    submission = world.submit(aid)

    assert submission.is_late and submission.score == 10
    standing = world.assignments.problem(world.student, world.room.id, aid).standing
    assert standing.state is StudentState.LATE


def test_past_the_deadline_without_late_work_the_posting_is_closed(
    world: World,
) -> None:
    aid = world.publish()
    world.submit(aid)
    world.clock.advance(timedelta(days=8))

    with pytest.raises(PostingClosedError):
        world.submit(aid)
    with pytest.raises(PostingClosedError):
        world.service.run(world.student, world.room.id, aid, "print(1)")
    view = world.service.page(world.student, world.room.id, aid)
    assert view.closed and not view.can_submit


def test_instructor_close_stops_submissions(world: World) -> None:
    aid = world.publish()
    world.assignments.close(world.teacher, world.room.id, aid)

    with pytest.raises(PostingClosedError):
        world.submit(aid)


def test_resubmission_off_allows_one_submit(world: World) -> None:
    aid = world.publish(allow_resubmission=False)
    world.submit(aid)

    with pytest.raises(ResubmissionNotAllowedError):
        world.submit(aid)
    assert not world.service.page(world.student, world.room.id, aid).can_submit


def test_empty_code_is_refused(world: World) -> None:
    aid = world.publish()

    with pytest.raises(EmptyCodeError):
        world.submit(aid, "   ")


def test_an_edit_marks_the_counted_submission_resubmit_needed(world: World) -> None:
    aid = world.publish()
    world.submit(aid)
    world.assignments.edit(world.teacher, aid, reason="Fixed test 3", title="New")

    view = world.service.page(world.student, world.room.id, aid)

    assert view.update is not None and view.update.reason == "Fixed test 3"
    standing = world.assignments.problem(world.student, world.room.id, aid).standing
    assert standing.state is StudentState.RESUBMIT_NEEDED


def test_instructor_cannot_submit_and_outsiders_see_nothing(world: World) -> None:
    aid = world.publish()

    with pytest.raises(PermissionDeniedError):
        world.service.submit(world.teacher, world.room.id, aid, "print(1)")
    with pytest.raises(PostingNotFoundError):
        world.service.page(world.teacher, world.room.id, aid + 99)
    with pytest.raises(ClassroomNotVisibleError):
        world.service.page(world.outsider, world.room.id, aid)


def test_results_view_counts_submitted_late_and_failing_tests(world: World) -> None:
    aid = world.publish()
    world.submit(aid)
    world.runner.outputs = {"1": "one"}
    world.submit(aid, who=world.other)

    view = world.service.page(world.teacher, world.room.id, aid)

    assert isinstance(view, InstructorResultsView)
    assert len(view.submitted) == 2 and view.all_passed == 1
    assert view.average_score == (10 + 2) / 2
    assert [f.rate for f in view.failures] == [0.0, 0.5, 0.5, 0.5]
    summary = world.assignments.problem(world.teacher, world.room.id, aid).summary
    assert (summary.submitted, summary.avg_score) == (2, 6.0)


def test_get_submission_is_for_its_student_or_the_instructor(world: World) -> None:
    aid = world.publish()
    submission = world.submit(aid)

    assert world.service.get(world.teacher, submission.id) == submission
    assert world.service.get(world.student, submission.id) == submission
    with pytest.raises(SubmissionNotFoundError):
        world.service.get(world.other, submission.id)
