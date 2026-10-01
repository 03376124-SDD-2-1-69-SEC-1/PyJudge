"""ClassroomStats computed on read from stored records (ADR-0007 §7, ADR-0008).

Fills the classrooms slice's `ClassroomStats` port, which C-01 reads, the way
`core/submissions/stats.py` fills `PostingStats`. Built only on repository
ports, so the contract in `tests/contracts/classroom_stats.py` runs it over the
fakes and over SQL alike. It reuses the domain's own rules: `counted_submissions`
for the Counted Submission, `Posting.is_closed` for Closed and
`Submission.all_passed` for Passed.
"""

from __future__ import annotations

from datetime import datetime

from questly.core.assignments.models import Posting
from questly.core.assignments.ports import PostingRepository
from questly.core.classrooms.models import (
    InstructorCardStats,
    StudentCardStats,
    StudentProgress,
)
from questly.core.classrooms.ports import ClassroomRepository, Clock
from questly.core.generation.models import DraftStatus
from questly.core.generation.ports import DraftRepository
from questly.core.submissions.ports import SubmissionRepository
from questly.core.submissions.service import counted_submissions


class ComputedClassroomStats:
    """The C-01 card numbers and the Student picker's progress line."""

    def __init__(
        self,
        postings: PostingRepository,
        submissions: SubmissionRepository,
        classrooms: ClassroomRepository,
        drafts: DraftRepository,
        clock: Clock,
    ) -> None:
        """Initialize the stats over the four repositories and a clock."""
        self._postings = postings
        self._submissions = submissions
        self._classrooms = classrooms
        self._drafts = drafts
        self._clock = clock

    def instructor_card(self, classroom_id: int) -> InstructorCardStats:
        """Problems posted, Drafts under review, and the average pass rate.

        Pass rate = current Members whose Counted Submission passed every
        test, summed over Postings, ÷ (Members × Postings); unknown when
        either is zero.
        """
        postings = self._postings.list_for_classroom(classroom_id)
        draft_count = sum(
            1
            for draft in self._drafts.list_for_classroom(classroom_id)
            if draft.status is DraftStatus.REVIEWING
        )
        members = {
            membership.student_id
            for membership in self._classrooms.list_memberships(classroom_id)
        }
        avg_pass_rate = None
        if members and postings:
            passed = sum(
                1
                for posting in postings
                for counted in counted_submissions(
                    self._submissions.list_for_posting(posting.id)
                )
                if counted.student_id in members and counted.all_passed
            )
            avg_pass_rate = passed / (len(members) * len(postings))
        return InstructorCardStats(
            problem_count=len(postings),
            draft_count=draft_count,
            avg_pass_rate=avg_pass_rate,
        )

    def student_card(self, classroom_id: int, student_id: int) -> StudentCardStats:
        """Open Postings the Student has not passed yet, and the nearest deadline."""
        now = self._clock.now()
        pending = [
            posting
            for posting in self._postings.list_for_classroom(classroom_id)
            if not posting.is_closed(now) and not self._passed(posting, student_id)
        ]
        if not pending:
            return StudentCardStats()
        next_deadline: datetime = min(posting.schedule.deadline for posting in pending)
        return StudentCardStats(pending_count=len(pending), next_deadline=next_deadline)

    def student_progress(
        self, student_id: int, classroom_ids: list[int]
    ) -> StudentProgress:
        """Solved (submitted at least once) and Passed, out of every Posting."""
        solved = total = passed = 0
        for classroom_id in classroom_ids:
            for posting in self._postings.list_for_classroom(classroom_id):
                total += 1
                mine = self._submissions.list_for_student(posting.id, student_id)
                if not mine:
                    continue
                solved += 1
                if self._passed(posting, student_id):
                    passed += 1
        return StudentProgress(solved=solved, total=total, passed=passed)

    def _passed(self, posting: Posting, student_id: int) -> bool:
        """Whether the Student's Counted Submission on a Posting passed it all."""
        counted = counted_submissions(
            self._submissions.list_for_student(posting.id, student_id)
        )
        return any(submission.all_passed for submission in counted)
