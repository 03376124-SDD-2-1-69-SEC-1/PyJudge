"""Contract for ClassroomStats computed from stored records (ADR-0007 §7).

The scenarios go in through the real repository ports, so a binding supplies
the four repositories (in-memory or SQL) and the contract builds the stats
from them. Bound in `tests/unit/core/classrooms/` and `tests/db/`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from questly.core.assignments.models import Posting, Schedule, TestCaseKind
from questly.core.assignments.ports import PostingRepository
from questly.core.classrooms.models import (
    InstructorCardStats,
    Membership,
    StudentCardStats,
    StudentProgress,
)
from questly.core.classrooms.ports import ClassroomRepository
from questly.core.generation.models import DraftStatus
from questly.core.generation.ports import DraftRepository
from questly.core.submissions.models import Submission, TestResult, Verdict
from questly.core.submissions.ports import SubmissionRepository
from questly.database.core.classroom_stats_repository import ComputedClassroomStats
from tests.contracts.draft_repository import draft
from tests.contracts.support import IdFactory, NeedsAssignments
from tests.fakes.auth import DEFAULT_NOW, FakeClock

NOW = DEFAULT_NOW


class ClassroomStatsContract(NeedsAssignments):
    """Checks that hold for the stats over any store behind the four ports."""

    @pytest.fixture()
    def clock(self) -> FakeClock:
        return FakeClock(NOW)

    @pytest.fixture()
    def stats(
        self,
        postings: PostingRepository,
        submissions: SubmissionRepository,
        classrooms: ClassroomRepository,
        drafts: DraftRepository,
        clock: FakeClock,
    ) -> ComputedClassroomStats:
        return ComputedClassroomStats(postings, submissions, classrooms, drafts, clock)

    # ---- helpers -------------------------------------------------------------

    def _post(
        self,
        postings: PostingRepository,
        classroom_id: int,
        assignment_id: int,
        *,
        deadline: timedelta = timedelta(days=7),
        allow_late: bool = False,
        closed: bool = False,
    ) -> Posting:
        return postings.create(
            Posting(
                classroom_id=classroom_id,
                assignment_id=assignment_id,
                schedule=Schedule(deadline=NOW + deadline, allow_late=allow_late),
                published_at=NOW - timedelta(days=1),
                closed_at=NOW - timedelta(hours=1) if closed else None,
            )
        )

    def _submit(
        self,
        submissions: SubmissionRepository,
        posting: Posting,
        student_id: int,
        *,
        passed: bool,
        minutes: int = 0,
        attempt: int = 1,
    ) -> None:
        verdict = Verdict.PASSED if passed else Verdict.WRONG_ANSWER
        submissions.add(
            Submission(
                posting_id=posting.id,
                classroom_id=posting.classroom_id,
                assignment_id=posting.assignment_id,
                student_id=student_id,
                version_number=1,
                code="print(1)",
                language="python3",
                submitted_at=NOW - timedelta(hours=2) + timedelta(minutes=minutes),
                is_late=False,
                score=10 if passed else 0,
                max_score=10,
                attempt=attempt,
                results=(
                    TestResult(
                        1, 1, TestCaseKind.SAMPLE, "", verdict, 0.1, "1", "1", ""
                    ),
                ),
            )
        )

    def _join(
        self, classrooms: ClassroomRepository, classroom_id: int, student_id: int
    ) -> None:
        classrooms.add_membership(Membership(classroom_id, student_id, NOW))

    # ---- instructor card -----------------------------------------------------

    def test_instructor_card_counts_postings_reviewing_drafts_and_pass_rate(
        self,
        stats: ComputedClassroomStats,
        postings: PostingRepository,
        submissions: SubmissionRepository,
        classrooms: ClassroomRepository,
        drafts: DraftRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
        new_user: IdFactory,
    ) -> None:
        room = new_classroom()
        alice, bob, gone = new_user(), new_user(), new_user()
        for student in (alice, bob, gone):
            self._join(classrooms, room, student)
        first = self._post(postings, room, new_assignment())
        self._post(postings, room, new_assignment())
        # Counted Submission is the latest: alice fails then passes, bob the
        # reverse; a Student who left counts in neither numerator nor
        # denominator.
        self._submit(submissions, first, alice, passed=False, minutes=0)
        self._submit(submissions, first, alice, passed=True, minutes=5, attempt=2)
        self._submit(submissions, first, bob, passed=True, minutes=0)
        self._submit(submissions, first, bob, passed=False, minutes=5, attempt=2)
        self._submit(submissions, first, gone, passed=True)
        classrooms.remove_membership(room, gone)
        author = new_user()
        drafts.create(draft(room, author))
        published = drafts.create(draft(room, author))
        drafts.update(replace(published, status=DraftStatus.PUBLISHED))

        card = stats.instructor_card(room)

        assert card == InstructorCardStats(
            problem_count=2, draft_count=1, avg_pass_rate=0.25
        )

    def test_pass_rate_is_unknown_without_members_or_postings(
        self,
        stats: ComputedClassroomStats,
        postings: PostingRepository,
        classrooms: ClassroomRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
        new_user: IdFactory,
    ) -> None:
        empty, no_members = new_classroom(), new_classroom()
        self._post(postings, no_members, new_assignment())
        no_postings = new_classroom()
        self._join(classrooms, no_postings, new_user())

        assert stats.instructor_card(empty) == InstructorCardStats()
        assert stats.instructor_card(no_members).avg_pass_rate is None
        assert stats.instructor_card(no_postings).avg_pass_rate is None

    # ---- student card --------------------------------------------------------

    def test_student_card_counts_open_postings_not_yet_passed(
        self,
        stats: ComputedClassroomStats,
        postings: PostingRepository,
        submissions: SubmissionRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
        new_user: IdFactory,
    ) -> None:
        room, student = new_classroom(), new_user()
        self._post(postings, room, new_assignment(), deadline=timedelta(days=5))
        failing = self._post(
            postings, room, new_assignment(), deadline=timedelta(days=2)
        )
        self._submit(submissions, failing, student, passed=False)
        passed = self._post(
            postings, room, new_assignment(), deadline=timedelta(days=1)
        )
        self._submit(submissions, passed, student, passed=True)
        self._post(postings, room, new_assignment(), closed=True)
        self._post(postings, room, new_assignment(), deadline=-timedelta(days=1))
        self._post(
            postings,
            room,
            new_assignment(),
            deadline=-timedelta(days=3),
            allow_late=True,
        )

        card = stats.student_card(room, student)

        assert card == StudentCardStats(
            pending_count=3, next_deadline=NOW - timedelta(days=3)
        )

    def test_student_card_with_nothing_pending(
        self,
        stats: ComputedClassroomStats,
        new_classroom: IdFactory,
        new_user: IdFactory,
    ) -> None:
        assert stats.student_card(new_classroom(), new_user()) == StudentCardStats()

    # ---- student progress ----------------------------------------------------

    def test_student_progress_across_the_given_classrooms(
        self,
        stats: ComputedClassroomStats,
        postings: PostingRepository,
        submissions: SubmissionRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
        new_user: IdFactory,
    ) -> None:
        one, two, elsewhere = new_classroom(), new_classroom(), new_classroom()
        student = new_user()
        solved_passed = self._post(postings, one, new_assignment())
        self._submit(submissions, solved_passed, student, passed=True)
        solved_failed = self._post(postings, two, new_assignment())
        self._submit(submissions, solved_failed, student, passed=False)
        self._post(postings, two, new_assignment())
        ignored = self._post(postings, elsewhere, new_assignment())
        self._submit(submissions, ignored, student, passed=True)

        assert stats.student_progress(student, [one, two]) == StudentProgress(
            solved=2, total=3, passed=1
        )
        assert stats.student_progress(student, []) == StudentProgress()
