"""Classroom domain model and the role-specific views its use cases return.

No FastAPI or database imports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ClassroomRole(StrEnum):
    """How an Actor relates to a Classroom."""

    OWNER = "owner"
    MEMBER = "member"
    OUTSIDER = "outsider"


class ClassroomFilter(StrEnum):
    """C-01 filter chips."""

    ALL = "all"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class Classroom:
    """One section of one course in one semester, owned by an Instructor.

    `join_code` is `None` while the Instructor has disabled joining.
    """

    instructor_id: int
    course_code: str
    course_name: str
    section: str
    semester: str
    join_code: str | None = None
    archived: bool = False
    id: int | None = None

    @property
    def label(self) -> str:
        """ "01076001 · Sec 1", as every header and card shows it."""
        return f"{self.course_code} · Sec {self.section}"


@dataclass(frozen=True, slots=True)
class Membership:
    """A Student's place in a Classroom."""

    classroom_id: int
    student_id: int
    joined_at: datetime
    id: int | None = None


@dataclass(frozen=True, slots=True)
class InstructorCardStats:
    """C-01 instructor card numbers that come from Assignments and Submissions."""

    problem_count: int = 0
    draft_count: int = 0
    avg_pass_rate: float | None = None


@dataclass(frozen=True, slots=True)
class StudentCardStats:
    """C-01 student card numbers: pending Assignments and the next deadline."""

    pending_count: int = 0
    next_deadline: datetime | None = None


@dataclass(frozen=True, slots=True)
class StudentProgress:
    """C-01 student summary bar: "Solved 12 of 15 · Passed 10"."""

    solved: int = 0
    total: int = 0
    passed: int = 0


@dataclass(frozen=True, slots=True)
class InstructorClassroomCard:
    classroom: Classroom
    student_count: int
    stats: InstructorCardStats


@dataclass(frozen=True, slots=True)
class StudentClassroomCard:
    classroom: Classroom
    instructor_name: str
    stats: StudentCardStats


@dataclass(frozen=True, slots=True)
class InstructorPicker:
    """C-01, instructor variant (01a when `cards` is empty)."""

    cards: list[InstructorClassroomCard] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class StudentPicker:
    """C-01, student variant (01b when `cards` is empty)."""

    progress: StudentProgress
    cards: list[StudentClassroomCard] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class InstructorClassroomView:
    """/classes/{id} for the Classroom's Instructor (T-01)."""

    classroom: Classroom
    student_count: int


@dataclass(frozen=True, slots=True)
class StudentClassroomView:
    """/classes/{id} for a Member (S-01)."""

    classroom: Classroom
    instructor_name: str


@dataclass(frozen=True, slots=True)
class MemberView:
    """A row of T-01 Members."""

    user_id: int
    full_name: str
    email: str
    student_number: str | None
    joined_at: datetime
