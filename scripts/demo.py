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
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI

from greader.core.assignments.models import (
    AssignmentContent,
    Difficulty,
    PostingSummary,
    Schedule,
    StudentStanding,
    StudentState,
    TestCase,
    TestCaseKind,
)
from greader.core.auth.models import Actor, InstructorRequest, Role, User
from greader.core.auth.pages import DemoAccount
from greader.core.classrooms.models import (
    Classroom,
    InstructorCardStats,
    Membership,
    StudentCardStats,
    StudentProgress,
)
from greader.core.generation.models import DocumentSummary
from greader.integrations.clock import SystemClock
from tests.fakes.app import build_app
from tests.fakes.assignments import FakePostingStats
from tests.fakes.auth import DEFAULT_PASSWORD, FakeAuthRepository, seed_user
from tests.fakes.classrooms import FakeClassroomRepository, FakeClassroomStats
from tests.fakes.generation import (
    FakeDocumentCatalog,
    FakeDraftRepository,
    FakeGenerationClient,
    binary_search_response,
)

BANGKOK = ZoneInfo("Asia/Bangkok")

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
# The prototype's six Programming I problems: title, difficulty, deadline
# (Bangkok date, 23:59), one sample test, one hidden test.
PROBLEMS = [
    ("Sum of a list", Difficulty.EASY, (9, 10), ("3\n1 2 3", "6"), ("0\n", "0")),
    ("Reverse a string", Difficulty.EASY, (9, 17), ("hello", "olleh"), ("a", "a")),
    (
        "Count word frequency",
        Difficulty.MEDIUM,
        (9, 24),
        ("the cat the", "the 2\ncat 1"),
        ("", ""),
    ),
    (
        "Binary search on sorted input",
        Difficulty.MEDIUM,
        (10, 1),
        ("5\n1 3 5 7 9\n7", "3"),
        ("4\n2 4 6 8\n5", "-1"),
    ),
    (
        "Matrix transpose",
        Difficulty.HARD,
        (10, 8),
        ("2 2\n1 2\n3 4", "1 3\n2 4"),
        ("1 1\n5", "5"),
    ),
    (
        "Stack with min()",
        Difficulty.HARD,
        (10, 15),
        ("push 3\nmin", "3"),
        ("min", "EMPTY"),
    ),
]
DATA_STRUCTURES = [
    ("Reverse a linked list", Difficulty.MEDIUM, (10, 5), ("1 2 3", "3 2 1"), ("", "")),
    (
        "Balanced parentheses",
        Difficulty.EASY,
        (10, 12),
        ("(()())", "YES"),
        ("(()", "NO"),
    ),
    (
        "Queue with two stacks",
        Difficulty.HARD,
        (10, 19),
        ("enq 1\ndeq", "1"),
        ("deq", "EMPTY"),
    ),
]
# T-01/S-01 numbers per problem until the submissions slice computes them:
# (submitted, avg score, fail rate), then per-student scores for Sec 1.
SEC1_SUMMARIES = [
    (6, 9.4, 0.06),
    (6, 9.0, 0.11),
    (5, 7.1, 0.32),
    (4, 6.3, 0.46),
    (1, None, 0.28),
    (0, None, None),
]
SEC1_SCORES = [  # student index -> score per problem (None = not started)
    [10, 10, 6, 4, None, None],
    [10, 9, 10, 10, 8, None],
    [8, 10, 7, 0, None, None],
    [10, 10, 9, 8, None, None],
    [10, 10, 5, None, None, None],
    [9, None, None, None, None, None],
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
        self.posting_stats = FakePostingStats()
        self.drafts = FakeDraftRepository()
        self.documents = FakeDocumentCatalog()
        # Every T-03 "Generate" answers with the prototype's binary-search draft.
        self.generation_client = FakeGenerationClient(binary_search_response())
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
        programming_1 = self.programming_1 = self._classroom(
            self.somchai, "01076001", "Programming I", "1", "X7K29B", self.students[:6]
        )
        programming_2 = self.programming_2 = self._classroom(
            self.somchai, "01076002", "Programming I", "2", "Q4M8TD", self.students[6:]
        )
        data_structures = self.data_structures = self._classroom(
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
            problem_count=3, avg_pass_rate=0.54
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


def _actor(user: User) -> Actor:
    return Actor(
        user_id=user.id, role=user.role, full_name=user.full_name, email=user.email
    )


def _deadline(month_day: tuple[int, int]) -> datetime:
    month, day = month_day
    return datetime(2026, month, day, 23, 59, tzinfo=BANGKOK).astimezone(UTC)


def _publish_problems(
    app: FastAPI, owner: User, problems: list, classroom_ids: list[int]
) -> list[int]:
    """Publish through the real use case; return the Sec-order posting ids."""
    service = app.state.assignment_service
    posting_ids = []
    for title, difficulty, deadline, sample, hidden in problems:
        published = service.publish(
            _actor(owner),
            AssignmentContent(
                title=title,
                problem_statement=f"{title}: read the input and print the answer.",
                difficulty=difficulty,
                test_cases=[
                    TestCase(input_data=sample[0], expected_output=sample[1]),
                    TestCase(
                        input_data=hidden[0],
                        expected_output=hidden[1],
                        kind=TestCaseKind.HIDDEN,
                        note="edge",
                    ),
                ],
            ),
            Schedule(deadline=_deadline(deadline)),
            classroom_ids,
        )
        posting_ids.append([p.id for p in published.postings])
    return posting_ids


def _seed_coursework(app: FastAPI, seed: DemoSeed) -> None:
    postings = _publish_problems(
        app,
        seed.somchai,
        PROBLEMS,
        [seed.programming_1.id, seed.programming_2.id],
    )
    _publish_problems(app, seed.warunee, DATA_STRUCTURES, [seed.data_structures.id])
    sec1_students = seed.students[:6]
    for index, (submitted, avg, fail) in enumerate(SEC1_SUMMARIES):
        sec1_posting = postings[index][0]
        seed.posting_stats.summaries[sec1_posting] = PostingSummary(
            submitted=submitted, avg_score=avg
        )
        if fail is not None:
            seed.posting_stats.fail_rates[sec1_posting] = fail
        for student, scores in zip(sec1_students, SEC1_SCORES, strict=True):
            score = scores[index]
            if score is None:
                continue
            state = StudentState.PASSED if score == 10 else StudentState.PARTIAL
            if student is seed.students[0] and index == 3:
                state = StudentState.RESUBMIT_NEEDED
            seed.posting_stats.standings[(sec1_posting, student.id)] = StudentStanding(
                state=state, score=score
            )


def _seed_generation(app: FastAPI, seed: DemoSeed) -> None:
    """Somchai's T-06 library and the T-01 draft "Stack with min() in O(1)"."""
    seed.documents.by_owner[seed.somchai.id] = [
        DocumentSummary(id=1, filename="lecture-06-searching.pdf", pages=24),
        DocumentSummary(id=2, filename="lecture-07-stacks.pdf", pages=18),
        DocumentSummary(id=3, filename="tutorial-03.pdf", pages=9),
    ]
    service = app.state.generation_service
    draft = service.generate(
        _actor(seed.somchai),
        seed.programming_1.id,
        prompt="A stack that returns its minimum in O(1).",
        difficulty=Difficulty.HARD,
        document_ids=[2],
    )
    service.save(
        _actor(seed.somchai),
        draft.id,
        title="Stack with min() in O(1)",
        problem_statement=(
            "Implement a stack with push, pop and min, each in O(1). Read one "
            "command per line and print the result of every min."
        ),
    )


def build_demo_app(seed: DemoSeed | None = None) -> FastAPI:
    """The demo application; `seed` is exposed so tests can inspect it."""
    if seed is None:
        seed = DemoSeed()
    app = _build(seed)
    _seed_coursework(app, seed)
    _seed_generation(app, seed)
    return app


def _build(seed: DemoSeed) -> FastAPI:
    # build_app already passes secure_cookies=False: the demo runs on plain
    # http://127.0.0.1, where some browsers refuse Secure cookies.
    return build_app(
        auth_repository=seed.users,
        clock=seed.clock,
        classroom_repository=seed.classrooms,
        classroom_stats=seed.stats,
        posting_stats=seed.posting_stats,
        draft_repository=seed.drafts,
        document_catalog=seed.documents,
        generation_client=seed.generation_client,
        demo_accounts=tuple(seed.accounts),
    )


def main() -> None:
    port = int(os.environ.get("GREADER_DEMO_PORT", "8000"))
    uvicorn.run(build_demo_app(), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
