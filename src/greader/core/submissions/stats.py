"""PostingStats computed on read from each Student's Counted Submission (§7).

Fills the assignments slice's `PostingStats` port, which T-01/S-01 read.
Authorization happens in AssignmentService before it asks for these numbers.
"""

from greader.core.assignments.models import (
    PostingSummary,
    StudentStanding,
    StudentState,
)
from greader.core.submissions.models import Submission
from greader.core.submissions.ports import AssignmentLookup, SubmissionRepository
from greader.core.submissions.service import counted_submissions


class SubmissionPostingStats:
    def __init__(
        self, submissions: SubmissionRepository, assignments: AssignmentLookup
    ) -> None:
        self._submissions = submissions
        self._assignments = assignments

    def posting_summary(self, posting_id: int) -> PostingSummary:
        counted = self._counted(posting_id)
        if not counted:
            return PostingSummary()
        scores = [submission.score for submission in counted.values()]
        return PostingSummary(
            submitted=len(counted), avg_score=round(sum(scores) / len(scores), 1)
        )

    def standing(self, posting_id: int, student_id: int) -> StudentStanding:
        counted = self._counted(posting_id).get(student_id)
        if counted is None:
            return StudentStanding()
        return StudentStanding(state=self._state(counted), score=counted.score)

    def score(self, posting_id: int, student_id: int) -> float | None:
        counted = self._counted(posting_id).get(student_id)
        if counted is None:
            return None
        return counted.score

    def fail_rate(self, posting_id: int) -> float | None:
        """Students who failed at least one test ÷ Students who submitted."""
        counted = self._counted(posting_id)
        if not counted:
            return None
        failed = sum(1 for submission in counted.values() if not submission.all_passed)
        return failed / len(counted)

    def _counted(self, posting_id: int) -> dict[int, Submission]:
        return {
            submission.student_id: submission
            for submission in counted_submissions(
                self._submissions.list_for_posting(posting_id)
            )
        }

    def _state(self, counted: Submission) -> StudentState:
        assignment = self._assignments.get(counted.assignment_id)
        if (
            assignment is not None
            and counted.version_number < assignment.current_version
        ):
            return StudentState.RESUBMIT_NEEDED
        if counted.is_late:
            return StudentState.LATE
        if counted.all_passed:
            return StudentState.PASSED
        return StudentState.PARTIAL
