"""Local demo mode: every page clickable before the schema exists.

    uv run python -m scripts.demo            # http://127.0.0.1:8000/login

Builds the app from the in-memory fakes in tests/fakes/ plus a small seed that
mirrors the sample data in docs/wireframes/ (Somchai's Programming I sections,
Warunee's Data Structures, students 66010001-66010010). Data lives in process
memory and is gone on restart. G-01 lists every seeded account under "log in
as"; all share one password. Verification links are logged, not emailed.

This never runs in production: create_app() without fakes still wires the
pending adapters that answer 503 until OPS-15 (ADR-0007 §10.4).
"""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI

from greader.core.auth.models import InstructorRequest, Role, User
from greader.core.auth.pages import DemoAccount
from greader.core.classrooms.models import (
    Classroom,
    InstructorCardStats,
    Membership,
    StudentCardStats,
    StudentProgress,
)
from greader.integrations.clock import SystemClock
from tests.fakes.app import build_app
from tests.fakes.auth import DEFAULT_PASSWORD, FakeAuthRepository, seed_user
from tests.fakes.classrooms import FakeClassroomRepository, FakeClassroomStats

STUDENTS = [
    ("66010001", "Nattapong Suwan"),
    ("66010002", "Pimchanok Wong"),
    ("66010003", "Kittisak Rat"),
    ("66010004", "Araya Nakorn"),
    ("66010005", "Thanawat Chai"),
    ("66010006", "Siriporn Mee"),
    ("66010007", "Jirayu Boon"),
    ("66010008", "Kanokwan Dee"),
    ("66010009", "Pakorn Lert"),
    ("66010010", "Wipada Sook"),
]
# Students who signed up with "I am an instructor" and wait in A-01.
REQUESTERS = [
    ("anan.t@kmitl.ac.th", "Anan Thong", "Information Technology"),
    ("preecha.s@kmitl.ac.th", "Preecha Sri", "Science"),
    ("malee.c@kmitl.ac.th", "Malee Chan", "Engineering"),
]


class DemoSeed:
    """The seeded repositories plus the accounts listed on G-01."""

    def __init__(self) -> None:
        self.clock = SystemClock()
        self.users = FakeAuthRepository()
        self.classrooms = FakeClassroomRepository()
        self.stats = FakeClassroomStats()
        self.accounts: list[DemoAccount] = []
        self._seed_accounts()
        self._seed_classrooms()

    def _user(self, email: str, name: str, role: Role, label: str) -> User:
        user = seed_user(self.users, email=email, full_name=name, role=role)
        self.accounts.append(
            DemoAccount(label=label, email=email, password=DEFAULT_PASSWORD)
        )
        return user

    def _seed_accounts(self) -> None:
        self.admin = self._user("admin@kmitl.ac.th", "Admin", Role.ADMIN, "Admin")
        self.somchai = self._user(
            "somchai.p@kmitl.ac.th",
            "Somchai Prasert",
            Role.INSTRUCTOR,
            "Somchai Prasert · instructor",
        )
        self.warunee = self._user(
            "warunee.k@kmitl.ac.th",
            "Warunee Kaew",
            Role.INSTRUCTOR,
            "Warunee Kaew · instructor",
        )
        self.students = []
        for number, name in STUDENTS:
            email = f"{number}@kmitl.ac.th"
            if len(self.students) < 2:
                self.students.append(
                    self._user(email, name, Role.STUDENT, f"{name} · student")
                )
            else:
                self.students.append(seed_user(self.users, email=email, full_name=name))
        for email, name, faculty in REQUESTERS:
            requester = seed_user(self.users, email=email, full_name=name)
            self.users.create_instructor_request(
                InstructorRequest(
                    user_id=requester.id, faculty=faculty, requested_at=self.clock.now()
                )
            )
        unverified = seed_user(
            self.users,
            email="new.student@kmitl.ac.th",
            full_name="New Student",
            verified=False,
        )
        self.accounts.append(
            DemoAccount(
                label="New Student · unverified (G-01b)",
                email=unverified.email,
                password=DEFAULT_PASSWORD,
            )
        )

    def _seed_classrooms(self) -> None:
        programming_1 = self._classroom(
            self.somchai, "01076001", "Programming I", "1", "X7K29B", self.students[:6]
        )
        programming_2 = self._classroom(
            self.somchai, "01076002", "Programming I", "2", "Q4M8TD", self.students[6:]
        )
        data_structures = self._classroom(
            self.warunee,
            "01076011",
            "Data Structures",
            "1",
            "H3PW7N",
            [self.students[0], self.students[1], self.students[6], self.students[7]],
        )
        # C-01 card numbers from the prototype, until the assignments and
        # submissions slices compute them.
        self.stats.instructor_cards[programming_1.id] = InstructorCardStats(
            problem_count=6, draft_count=1, avg_pass_rate=0.78
        )
        self.stats.instructor_cards[programming_2.id] = InstructorCardStats(
            problem_count=6, avg_pass_rate=0.65
        )
        self.stats.instructor_cards[data_structures.id] = InstructorCardStats(
            problem_count=9, draft_count=2, avg_pass_rate=0.54
        )
        nattapong = self.students[0]
        self.stats.progress[nattapong.id] = StudentProgress(
            solved=12, total=15, passed=10
        )
        self.stats.student_cards[(programming_1.id, nattapong.id)] = StudentCardStats(
            pending_count=2
        )
        self.stats.student_cards[(data_structures.id, nattapong.id)] = StudentCardStats(
            pending_count=1
        )

    def _classroom(
        self,
        owner: User,
        course_code: str,
        course_name: str,
        section: str,
        join_code: str,
        members: list[User],
    ) -> Classroom:
        classroom = self.classrooms.create(
            Classroom(
                instructor_id=owner.id,
                course_code=course_code,
                course_name=course_name,
                section=section,
                semester="1/2569",
                join_code=join_code,
            )
        )
        for member in members:
            self.classrooms.add_membership(
                Membership(
                    classroom_id=classroom.id,
                    student_id=member.id,
                    joined_at=self.clock.now(),
                )
            )
        return classroom


def build_demo_app(seed: DemoSeed | None = None) -> FastAPI:
    """The demo application; `seed` is exposed so tests can inspect it."""
    if seed is None:
        seed = DemoSeed()
    return build_app(
        auth_repository=seed.users,
        clock=seed.clock,
        classroom_repository=seed.classrooms,
        classroom_stats=seed.stats,
        demo_accounts=tuple(seed.accounts),
    )


def main() -> None:
    port = int(os.environ.get("GREADER_DEMO_PORT", "8000"))
    uvicorn.run(build_demo_app(), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
