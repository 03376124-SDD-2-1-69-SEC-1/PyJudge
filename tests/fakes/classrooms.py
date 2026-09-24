"""In-memory ClassroomRepository and a settable ClassroomStats."""

from __future__ import annotations

from dataclasses import replace

from greader.core.classrooms.models import (
    Classroom,
    InstructorCardStats,
    Membership,
    StudentCardStats,
    StudentProgress,
)


class FakeClassroomRepository:
    def __init__(self) -> None:
        self._classrooms: dict[int, Classroom] = {}
        self._memberships: dict[int, Membership] = {}
        self._next_id = 1

    def _new_id(self) -> int:
        new_id = self._next_id
        self._next_id += 1
        return new_id

    def get(self, classroom_id: int) -> Classroom | None:
        return self._classrooms.get(classroom_id)

    def list_owned_by(self, instructor_id: int) -> list[Classroom]:
        return [
            self._classrooms[key]
            for key in sorted(self._classrooms)
            if self._classrooms[key].instructor_id == instructor_id
        ]

    def list_joined_by(self, student_id: int) -> list[Classroom]:
        joined = {
            membership.classroom_id
            for membership in self._memberships.values()
            if membership.student_id == student_id
        }
        return [self._classrooms[key] for key in sorted(joined)]

    def find_by_join_code(self, join_code: str) -> Classroom | None:
        for classroom in self._classrooms.values():
            if classroom.join_code == join_code:
                return classroom
        return None

    def create(self, classroom: Classroom) -> Classroom:
        created = replace(classroom, id=self._new_id())
        self._classrooms[created.id] = created
        return created

    def update(self, classroom: Classroom) -> Classroom:
        self._classrooms[classroom.id]  # KeyError for an unknown id
        self._classrooms[classroom.id] = classroom
        return classroom

    def get_membership(self, classroom_id: int, student_id: int) -> Membership | None:
        for membership in self._memberships.values():
            if (membership.classroom_id, membership.student_id) == (
                classroom_id,
                student_id,
            ):
                return membership
        return None

    def list_memberships(self, classroom_id: int) -> list[Membership]:
        return [
            self._memberships[key]
            for key in sorted(self._memberships)
            if self._memberships[key].classroom_id == classroom_id
        ]

    def add_membership(self, membership: Membership) -> Membership:
        created = replace(membership, id=self._new_id())
        self._memberships[created.id] = created
        return created

    def remove_membership(self, classroom_id: int, student_id: int) -> bool:
        membership = self.get_membership(classroom_id, student_id)
        if membership is None:
            return False
        del self._memberships[membership.id]
        return True


class FakeClassroomStats:
    """Zero everywhere unless a test or the demo seed sets a value."""

    def __init__(self) -> None:
        self.instructor_cards: dict[int, InstructorCardStats] = {}
        self.student_cards: dict[tuple[int, int], StudentCardStats] = {}
        self.progress: dict[int, StudentProgress] = {}

    def instructor_card(self, classroom_id: int) -> InstructorCardStats:
        if classroom_id in self.instructor_cards:
            return self.instructor_cards[classroom_id]
        return InstructorCardStats()

    def student_card(self, classroom_id: int, student_id: int) -> StudentCardStats:
        if (classroom_id, student_id) in self.student_cards:
            return self.student_cards[(classroom_id, student_id)]
        return StudentCardStats()

    def student_progress(
        self, student_id: int, classroom_ids: list[int]
    ) -> StudentProgress:
        if student_id in self.progress:
            return self.progress[student_id]
        return StudentProgress()
