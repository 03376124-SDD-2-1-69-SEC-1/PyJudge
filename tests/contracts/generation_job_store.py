import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from questly.core.assignments.models import Difficulty
from questly.core.auth.models import Actor, Role
from questly.core.generation.models import (
    GenerationForm,
    GenerationJob,
    GenerationStep,
    JobStatus,
    StartedJob,
)
from questly.core.generation.ports import GenerationJobStore

T0 = datetime(2026, 10, 12, 3, 0, tzinfo=UTC)


def job_of(user_id: int = 1, classroom_id: int = 7) -> GenerationJob:
    return GenerationJob(
        actor=Actor(user_id=user_id, role=Role.INSTRUCTOR, full_name="n", email="e"),
        classroom_id=classroom_id,
        form=GenerationForm(
            prompt="p", difficulty=Difficulty.EASY, topic_id=None, document_ids=[]
        ),
        started_at=T0,
    )


class GenerationJobStoreContractTests:
    """Contract tests for GenerationJobStore implementations (Fake & in-memory)."""

    def test_a_created_job_gets_an_id_and_get_reads_it_back(
        self, store: GenerationJobStore
    ) -> None:
        started = store.create_unless_running(job_of())

        assert started.created is True
        assert started.job.id is not None
        assert store.get(started.job.id) == started.job

    def test_jobs_in_different_classrooms_or_of_different_users_get_distinct_ids(
        self, store: GenerationJobStore
    ) -> None:
        ids = {
            store.create_unless_running(job_of(1, 7)).job.id,
            store.create_unless_running(job_of(1, 8)).job.id,
            store.create_unless_running(job_of(2, 7)).job.id,
        }

        assert len(ids) == 3

    def test_a_second_create_returns_the_job_still_running(
        self, store: GenerationJobStore
    ) -> None:
        first = store.create_unless_running(job_of())

        second = store.create_unless_running(job_of())

        assert second.created is False
        assert second.job.id == first.job.id

    def test_a_job_that_ended_does_not_block_a_new_one(
        self, store: GenerationJobStore
    ) -> None:
        first = store.create_unless_running(job_of())
        store.update(first.job.id, lambda job: job.cancel())

        second = store.create_unless_running(job_of())

        assert second.created is True
        assert second.job.id != first.job.id

    def test_simultaneous_creates_for_one_user_make_exactly_one_job(
        self, store: GenerationJobStore, make_store: Callable[[], GenerationJobStore]
    ) -> None:
        # Switch threads far more often than usual and repeat, so a store that
        # checks and then inserts without a lock fails here and not once a year.
        previous = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            for _ in range(150):
                assert _clicks_at_once(make_store(), clicks=30) == 1
        finally:
            sys.setswitchinterval(previous)

    def test_get_of_an_unknown_id_is_none(self, store: GenerationJobStore) -> None:
        assert store.get(123456789) is None

    def test_update_applies_the_change_to_the_stored_job(
        self, store: GenerationJobStore
    ) -> None:
        created = store.create_unless_running(job_of()).job

        updated = store.update(
            created.id, lambda job: job.advance(GenerationStep.VALIDATING, T0)
        )

        assert updated.step is GenerationStep.VALIDATING
        assert store.get(created.id) == updated

    def test_a_change_that_raises_leaves_the_job_untouched(
        self, store: GenerationJobStore
    ) -> None:
        created = store.create_unless_running(job_of()).job

        def boom(job: GenerationJob) -> GenerationJob:
            raise RuntimeError

        with pytest.raises(RuntimeError):
            store.update(created.id, boom)

        assert store.get(created.id) == created

    def test_update_of_an_unknown_id_raises_key_error(
        self, store: GenerationJobStore
    ) -> None:
        with pytest.raises(KeyError):
            store.update(123456789, lambda job: job)

    def test_running_for_finds_only_this_users_running_job_in_this_classroom(
        self, store: GenerationJobStore
    ) -> None:
        mine = store.create_unless_running(job_of(user_id=1, classroom_id=7)).job
        store.create_unless_running(job_of(user_id=2, classroom_id=7))
        store.create_unless_running(job_of(user_id=1, classroom_id=8))

        assert store.running_for(1, 7) == mine
        assert store.running_for(1, 9) is None

        store.update(mine.id, lambda job: job.cancel())
        assert store.get(mine.id).status is JobStatus.CANCELLED
        assert store.running_for(1, 7) is None


def _clicks_at_once(store: GenerationJobStore, clicks: int) -> int:
    """How many of `clicks` simultaneous creates made a new job."""
    results: list[StartedJob] = []

    def click() -> None:
        results.append(store.create_unless_running(job_of()))

    threads = [threading.Thread(target=click) for _ in range(clicks)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return sum(1 for started in results if started.created)
