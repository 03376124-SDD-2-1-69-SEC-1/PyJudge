"""DueSoonService: "Deadline tomorrow", computed from Postings and standings."""

from datetime import timedelta

import pytest

from questly.core.assignments.models import (
    AssignmentContent,
    Difficulty,
    Schedule,
    StudentStanding,
    StudentState,
    TestCase,
)
from questly.core.assignments.service import AssignmentService
from questly.core.auth.models import Actor, Role, UserSummary
from questly.core.classrooms.service import ClassroomService
from questly.core.notifications.models import DueSoon
from questly.core.notifications.service import DueSoonService
from tests.fakes.assignments import (
    FakeAssignmentRepository,
    FakePostingRepository,
    FakePostingStats,
    FakeVersionRepository,
)
from tests.fakes.auth import FakeAuthRepository, FakeClock, seed_user
from tests.fakes.classrooms import FakeClassroomRepository, FakeClassroomStats
from tests.fakes.notifications import RecordingMemberNotifier


class World:
    def __init__(self) -> None:
        self.clock = FakeClock()
        self.users = FakeAuthRepository()
        self.classrooms = ClassroomService(
            FakeClassroomRepository(),
            _Directory(),
            FakeClassroomStats(),
            self.clock,
        )
        self.stats = FakePostingStats()
        self.assignments = AssignmentService(
            FakeAssignmentRepository(),
            FakeVersionRepository(),
            FakePostingRepository(),
            self.classrooms,
            self.stats,
            self.clock,
            RecordingMemberNotifier(),
        )
        self.service = DueSoonService(self.classrooms, self.assignments, self.clock)
        self.teacher = self._actor("somchai.p@kmitl.ac.th", Role.INSTRUCTOR)
        self.student = self._actor("66010001@kmitl.ac.th", Role.STUDENT)
        self.admin = self._actor("admin@kmitl.ac.th", Role.ADMIN)
        self.sec1 = self._classroom("1")
        self.classrooms.join(self.student, self.sec1.join_code)

    def _actor(self, email: str, role: Role) -> Actor:
        user = seed_user(self.users, email=email, full_name=email, role=role)
        return Actor(user_id=user.id, role=role, full_name=email, email=email)

    def _classroom(self, section: str):
        return self.classrooms.create(
            self.teacher,
            course_code="01076001",
            course_name="Programming I",
            section=section,
            semester="1/2569",
        )

    def publish(self, title: str, due_in: timedelta, classroom_id: int | None = None):
        if classroom_id is None:
            classroom_id = self.sec1.id
        return self.assignments.publish(
            self.teacher,
            AssignmentContent(
                title=title,
                problem_statement="Print the answer.",
                difficulty=Difficulty.EASY,
                test_cases=[TestCase(input_data="1", expected_output="1")],
            ),
            Schedule(deadline=self.clock.now() + due_in),
            [classroom_id],
        )


class _Directory:
    def summaries(self, user_ids: list[int]) -> list[UserSummary]:
        return []


@pytest.fixture()
def world() -> World:
    return World()


def test_lists_unsubmitted_postings_due_within_24_hours_soonest_first(
    world: World,
) -> None:
    later = world.publish("Later today", timedelta(hours=20))
    sooner = world.publish("Very soon", timedelta(hours=2))
    world.publish("Next week", timedelta(days=7))
    world.publish("Just outside", timedelta(hours=24, minutes=1))

    assert world.service.due_soon(world.student) == [
        DueSoon(
            classroom_id=world.sec1.id,
            assignment_id=sooner.assignment.id,
            title="Very soon",
            deadline=world.clock.now() + timedelta(hours=2),
        ),
        DueSoon(
            classroom_id=world.sec1.id,
            assignment_id=later.assignment.id,
            title="Later today",
            deadline=world.clock.now() + timedelta(hours=20),
        ),
    ]


def test_leaves_out_submitted_closed_overdue_and_archived(world: World) -> None:
    submitted = world.publish("Submitted", timedelta(hours=3))
    world.stats.standings[(submitted.postings[0].id, world.student.user_id)] = (
        StudentStanding(state=StudentState.PARTIAL, score=4)
    )
    closed = world.publish("Closed", timedelta(hours=3))
    world.assignments.close(world.teacher, world.sec1.id, closed.assignment.id)
    world.publish("Overdue", timedelta(hours=-1))
    archived = world._classroom("2")
    world.classrooms.join(world.student, archived.join_code)
    world.publish("In an archived classroom", timedelta(hours=3), archived.id)
    world.classrooms.archive(world.teacher, archived.id)

    assert world.service.due_soon(world.student) == []


def test_only_students_have_deadlines(world: World) -> None:
    world.publish("Very soon", timedelta(hours=2))

    assert world.service.due_soon(world.teacher) == []
    assert world.service.due_soon(world.admin) == []
