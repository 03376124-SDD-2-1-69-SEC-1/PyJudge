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
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI

from greader.core.assignments.models import (
    AssignmentContent,
    Difficulty,
    PublishedAssignment,
    Schedule,
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
from greader.core.submissions.models import Submission, TestResult, Verdict
from greader.core.submissions.service import score_for
from greader.integrations.clock import SystemClock
from tests.fakes.app import build_app
from tests.fakes.auth import DEFAULT_PASSWORD, FakeAuthRepository, seed_user
from tests.fakes.classrooms import FakeClassroomRepository, FakeClassroomStats
from tests.fakes.generation import (
    FakeDocumentCatalog,
    FakeDraftRepository,
    FakeGenerationClient,
    binary_search_response,
)
from tests.fakes.submissions import FakeSubmissionRepository, LocalPythonRunner

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
# Binary search gets the prototype's six Test Cases (2 sample, 3 hidden,
# 1 edge); every other problem has one sample and one hidden test.
BINARY_SEARCH_TESTS = [
    TestCase(input_data="5\n1 3 5 7 9\n7", expected_output="3"),
    TestCase(input_data="4\n2 4 6 8\n5", expected_output="-1"),
    TestCase(
        input_data="0\n\n1",
        expected_output="-1",
        kind=TestCaseKind.HIDDEN,
        note="empty list",
    ),
    TestCase(
        input_data="6\n1 2 3 4 5 6\n6",
        expected_output="5",
        kind=TestCaseKind.HIDDEN,
        note="last item",
    ),
    TestCase(
        input_data="3\n1 3 5\n1",
        expected_output="0",
        kind=TestCaseKind.HIDDEN,
        note="first item",
    ),
    TestCase(
        input_data="5\n1 2 2 2 3\n2",
        expected_output="2",
        kind=TestCaseKind.EDGE,
        note="duplicates",
    ),
]
BINARY_SEARCH_CODE = """def binary_search(nums, x):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == x:
            return mid
        elif nums[mid] < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


n = int(input())
nums = list(map(int, input().split()))
x = int(input())
print(binary_search(nums, x))
"""
# Sec 1 Submissions: per student, per problem, the tests passed on each
# attempt (oldest first); None = never submitted. Tests pass in order, so
# "4" on binary search passes both samples and two hidden tests.
SEC1_ATTEMPTS = [
    [[2], [2], [1], [2, 4, 4], None, None],
    [[2], [1, 2], [2], [6], [1], None],
    [[1, 2], [2], [1], [0], None, None],
    [[2], [2], [2], [3, 5], None, None],
    [[2], [2], [1], None, None, None],
    [[1], None, None, None, None, None],
]
# Students whose failing tests crash instead of printing a wrong answer
# (S-02d), and the Sec 1 problem that takes late work (S-02 "Late").
CRASHING_STUDENT = 2
LATE_PROBLEM = 1
BINARY_SEARCH = 3
UPDATE_REASON = "Test case 3 had a wrong expected output."

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
        self.submissions = FakeSubmissionRepository()
        # Run and Submit execute with this machine's Python (demo only).
        self.code_runner = LocalPythonRunner()
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
) -> list[PublishedAssignment]:
    """Publish through the real use case, in problem-number order."""
    service = app.state.assignment_service
    published = []
    for title, difficulty, deadline, sample, hidden in problems:
        test_cases = [
            TestCase(input_data=sample[0], expected_output=sample[1]),
            TestCase(
                input_data=hidden[0],
                expected_output=hidden[1],
                kind=TestCaseKind.HIDDEN,
                note="edge",
            ),
        ]
        if title == "Binary search on sorted input":
            test_cases = BINARY_SEARCH_TESTS
        published.append(
            service.publish(
                _actor(owner),
                AssignmentContent(
                    title=title,
                    problem_statement=f"{title}: read the input and print the answer.",
                    difficulty=difficulty,
                    test_cases=test_cases,
                ),
                Schedule(deadline=_deadline(deadline)),
                classroom_ids,
            )
        )
    return published


def _seed_coursework(app: FastAPI, seed: DemoSeed) -> None:
    published = _publish_problems(
        app,
        seed.somchai,
        PROBLEMS,
        [seed.programming_1.id, seed.programming_2.id],
    )
    _publish_problems(app, seed.warunee, DATA_STRUCTURES, [seed.data_structures.id])
    _seed_submissions(app, seed, [item.assignment.id for item in published])


def _seed_submissions(app: FastAPI, seed: DemoSeed, assignment_ids: list[int]) -> None:
    """Graded Sec 1 Submissions, so T-01/S-01/T-02 numbers are computed."""
    service = app.state.assignment_service
    somchai = _actor(seed.somchai)
    sec1 = seed.programming_1.id
    service.update_posting(somchai, sec1, assignment_ids[LATE_PROBLEM], allow_late=True)
    # Binary search changed after Nattapong's last attempt: S-02e for him and
    # two Versions on T-02b; everyone else submitted on Version 2.
    binary_search = service.problem(somchai, sec1, assignment_ids[BINARY_SEARCH])
    service.edit(
        somchai,
        binary_search.assignment.id,
        reason=UPDATE_REASON,
        test_cases=binary_search.assignment.test_cases,
    )
    now = seed.clock.now()
    for index, assignment_id in enumerate(assignment_ids):
        problem = service.problem(somchai, sec1, assignment_id)
        schedule = problem.posting.schedule
        for student_index, (student, attempts) in enumerate(
            zip(seed.students[:6], SEC1_ATTEMPTS, strict=True)
        ):
            passes = attempts[index]
            if passes is None:
                continue
            version = problem.assignment.current_version
            if index == BINARY_SEARCH and student_index == 0:
                version -= 1
            for attempt, passed in enumerate(passes, start=1):
                submitted_at = min(now, schedule.deadline) - timedelta(
                    days=len(passes) - attempt + 1, hours=student_index
                )
                if index == LATE_PROBLEM and student_index == CRASHING_STUDENT:
                    submitted_at = schedule.deadline + timedelta(days=2)
                results = _results(
                    problem.assignment.test_cases,
                    passed,
                    crash=student_index == CRASHING_STUDENT,
                )
                seed.submissions.add(
                    Submission(
                        posting_id=problem.posting.id,
                        classroom_id=sec1,
                        assignment_id=assignment_id,
                        student_id=student.id,
                        version_number=version,
                        code=BINARY_SEARCH_CODE
                        if index == BINARY_SEARCH
                        else f"# attempt {attempt}\nprint(input())\n",
                        language="python3",
                        submitted_at=submitted_at,
                        is_late=submitted_at > schedule.deadline,
                        score=score_for(results, schedule.max_score),
                        max_score=schedule.max_score,
                        attempt=attempt,
                        results=results,
                    )
                )


def _results(
    test_cases: list[TestCase], passed: int, *, crash: bool
) -> tuple[TestResult, ...]:
    """The first `passed` tests pass; the rest fail or crash."""
    failing = Verdict.RUNTIME_ERROR if crash else Verdict.WRONG_ANSWER
    kinds: dict[TestCaseKind, int] = {}
    results = []
    for position, test_case in enumerate(test_cases, start=1):
        kinds[test_case.kind] = kinds.get(test_case.kind, 0) + 1
        ok = position <= passed
        results.append(
            TestResult(
                position=position,
                ordinal=kinds[test_case.kind],
                kind=test_case.kind,
                note=test_case.note,
                verdict=Verdict.PASSED if ok else failing,
                time_seconds=0.02,
                expected_output=test_case.expected_output,
                actual_output=test_case.expected_output if ok else "0",
                error=""
                if ok or not crash
                else "Traceback (most recent call last):\n"
                '  File "<string>", line 7, in binary_search\n'
                "IndexError: list index out of range",
            )
        )
    return tuple(results)


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
        submission_repository=seed.submissions,
        code_runner=seed.code_runner,
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
