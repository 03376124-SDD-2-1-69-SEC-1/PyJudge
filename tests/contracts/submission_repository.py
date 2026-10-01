"""Contract every SubmissionRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/submissions/` and to
`SQLSubmissionRepository` in `tests/db/`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from questly.core.assignments.models import TestCaseKind
from questly.core.submissions.models import Submission, TestResult, Verdict
from questly.core.submissions.ports import SubmissionRepository
from tests.contracts.support import IdFactory, NeedsPostings, PostingFactory, PostingIds

NOW = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)


def result(position: int, verdict: Verdict = Verdict.PASSED) -> TestResult:
    return TestResult(
        position=position,
        ordinal=position,
        kind=TestCaseKind.HIDDEN if position > 1 else TestCaseKind.SAMPLE,
        note="" if position == 1 else f"case {position}",
        verdict=verdict,
        time_seconds=0.25,
        expected_output="3",
        actual_output="3" if verdict is Verdict.PASSED else "4",
        error="",
    )


def submission(
    where: PostingIds, student_id: int, attempt: int = 1, at: datetime = NOW
) -> Submission:
    return Submission(
        posting_id=where.posting_id,
        classroom_id=where.classroom_id,
        assignment_id=where.assignment_id,
        student_id=student_id,
        version_number=1,
        code="print(sum(map(int, input().split())))",
        language="python3",
        submitted_at=at,
        is_late=False,
        score=6,
        max_score=10,
        attempt=attempt,
        results=(result(1), result(2, Verdict.WRONG_ANSWER), result(3)),
    )


class SubmissionRepositoryContract(NeedsPostings):
    """Checks that hold for any store behind SubmissionRepository."""

    def test_add_assigns_id_and_round_trips_every_result(
        self,
        repository: SubmissionRepository,
        new_posting: PostingFactory,
        new_user: IdFactory,
    ) -> None:
        added = repository.add(submission(new_posting(), new_user()))

        assert isinstance(added.id, int)
        assert repository.get(added.id) == added
        assert [r.verdict for r in added.results] == [
            Verdict.PASSED,
            Verdict.WRONG_ANSWER,
            Verdict.PASSED,
        ]

    def test_get_on_unknown_id_returns_none(
        self, repository: SubmissionRepository
    ) -> None:
        assert repository.get(999_999) is None

    def test_list_for_student_is_oldest_first_and_filtered(
        self,
        repository: SubmissionRepository,
        new_posting: PostingFactory,
        new_user: IdFactory,
    ) -> None:
        where, other_place = new_posting(), new_posting()
        alice, bob = new_user(), new_user()
        later = repository.add(
            submission(where, alice, attempt=2, at=NOW + timedelta(hours=1))
        )
        earlier = repository.add(submission(where, alice, attempt=1, at=NOW))
        repository.add(submission(where, bob))
        repository.add(submission(other_place, alice))

        assert repository.list_for_student(where.posting_id, alice) == (
            earlier,
            later,
        )

    def test_list_for_posting_returns_every_student_oldest_first(
        self,
        repository: SubmissionRepository,
        new_posting: PostingFactory,
        new_user: IdFactory,
    ) -> None:
        where = new_posting()
        alice, bob = new_user(), new_user()
        second = repository.add(submission(where, bob, at=NOW + timedelta(minutes=5)))
        first = repository.add(submission(where, alice, at=NOW))

        assert repository.list_for_posting(where.posting_id) == (first, second)
        assert repository.list_for_posting(999_999) == ()
