"""GenerationService jobs: background Generate and the T-03c progress page."""

from datetime import timedelta

import pytest

from questly.core.assignments.models import Difficulty
from questly.core.auth.models import PermissionDeniedError
from questly.core.generation.models import (
    STALE_AFTER,
    GenerationJob,
    GenerationStep,
    JobError,
    JobStatus,
    ProviderQuotaSnapshot,
    QuotaKind,
    StartedJob,
)
from questly.core.generation.service import (
    ClassroomNotVisibleError,
    DocumentNotAllowedError,
    GenerationJobGoneError,
    ProviderQuotaExceededError,
    QuotaExceededError,
)
from tests.unit.core.generation.world import World


def start_result(world: World, **overrides: object) -> StartedJob:
    arguments: dict[str, object] = {
        "prompt": "Binary search",
        "difficulty": Difficulty.MEDIUM,
        "document_ids": [1],
    }
    return world.service.start_job(
        world.teacher, world.sec1.id, **{**arguments, **overrides}
    )


def start(world: World, **overrides: object) -> GenerationJob:
    return start_result(world, **overrides).job


def test_the_provider_quota_is_spent_only_when_exact_and_empty() -> None:
    assert exhausted().is_spent
    assert not World().provider_quota.current.is_spent
    unmeasured = ProviderQuotaSnapshot(
        kind=QuotaKind.UNKNOWN, resets_at=exhausted().resets_at, note="n"
    )
    assert not unmeasured.is_spent


def exhausted() -> ProviderQuotaSnapshot:
    return ProviderQuotaSnapshot(
        kind=QuotaKind.EXACT,
        used=50,
        limit=50,
        remaining=0,
        resets_at=World().clock.now(),
        note="",
    )


# ---- start_job ------------------------------------------------------------


def test_start_job_creates_a_running_job_and_generates_nothing_yet(
    world: World,
) -> None:
    job = start(world)

    assert job.id is not None
    assert job.status is JobStatus.RUNNING
    assert job.form.prompt == "Binary search"
    assert job.form.document_ids == [1]
    assert world.client.requests == []
    assert world.service.quota(world.teacher).used == 0


def test_a_second_start_returns_the_job_already_running(world: World) -> None:
    first = start_result(world)

    second = start_result(world, prompt="Something else")

    assert first.created is True
    assert second.created is False
    assert second.job.id == first.job.id
    assert second.job.form.prompt == "Binary search"


def test_a_job_in_another_classroom_does_not_block_a_new_one(world: World) -> None:
    first = start(world)

    other = world.service.start_job(
        world.teacher, world.sec2.id, prompt="Sorting", difficulty=Difficulty.EASY
    )

    assert other.created is True
    assert other.job.id != first.id


def test_a_stale_running_job_does_not_block_a_new_one(world: World) -> None:
    first = start(world)
    world.clock.advance(STALE_AFTER + timedelta(seconds=1))

    second = start(world)

    assert second.id != first.id
    assert world.jobs.get(first.id).status is JobStatus.FAILED


def test_start_job_rejects_an_empty_prompt(world: World) -> None:
    with pytest.raises(ValueError):
        start(world, prompt="   ")


def test_start_job_rejects_a_document_that_is_not_the_instructors(
    world: World,
) -> None:
    with pytest.raises(DocumentNotAllowedError):
        start(world, document_ids=[99])


def test_start_job_stops_when_the_daily_quota_is_spent() -> None:
    world = World(quota=1)
    world.generate()

    with pytest.raises(QuotaExceededError):
        start(world)


def test_start_job_stops_when_the_provider_free_quota_is_spent(world: World) -> None:
    world.provider_quota.current = exhausted()

    with pytest.raises(ProviderQuotaExceededError):
        start(world)

    assert world.jobs.running_for(world.teacher.user_id, world.sec1.id) is None


@pytest.mark.parametrize("kind", [QuotaKind.UNKNOWN, QuotaKind.DEMO])
def test_an_unmeasured_provider_quota_never_blocks(
    world: World, kind: QuotaKind
) -> None:
    world.provider_quota.current = ProviderQuotaSnapshot(
        kind=kind, resets_at=world.clock.now(), note="not measured"
    )

    assert start(world).status is JobStatus.RUNNING


def test_a_student_cannot_start_a_job(world: World) -> None:
    with pytest.raises(PermissionDeniedError):
        world.service.start_job(
            world.student, world.sec1.id, prompt="x", difficulty=Difficulty.EASY
        )


def test_an_outsider_cannot_start_a_job(world: World) -> None:
    with pytest.raises(ClassroomNotVisibleError):
        world.service.start_job(
            world.other, world.sec1.id, prompt="x", difficulty=Difficulty.EASY
        )


# ---- run_job --------------------------------------------------------------


def test_run_job_saves_the_draft_and_records_every_step(world: World) -> None:
    job = start(world)

    world.service.run_job(world.teacher, world.sec1.id, job.id)

    done = world.jobs.get(job.id)
    assert done.status is JobStatus.DONE
    assert done.draft_id is not None
    assert [t.step for t in done.completed] == [
        GenerationStep.CALLING_MODEL,
        GenerationStep.VALIDATING,
        GenerationStep.SAVING,
    ]
    assert world.service.quota(world.teacher).used == 1


def test_run_job_refreshes_the_provider_quota_after_a_success(world: World) -> None:
    job = start(world)

    world.service.run_job(world.teacher, world.sec1.id, job.id)

    assert world.provider_quota.invalidations == 1


def test_a_failed_run_ends_the_job_without_charging_anything(world: World) -> None:
    world.client.fail = True
    job = start(world)

    world.service.run_job(world.teacher, world.sec1.id, job.id)

    failed = world.jobs.get(job.id)
    assert failed.status is JobStatus.FAILED
    assert failed.error is JobError.FAILED
    assert world.service.quota(world.teacher).used == 0
    assert world.provider_quota.invalidations == 0


def test_a_run_for_a_job_that_is_gone_is_refused(world: World) -> None:
    with pytest.raises(GenerationJobGoneError):
        world.service.run_job(world.teacher, world.sec1.id, 424242)

    assert world.client.requests == []


def test_another_instructor_cannot_run_the_job(world: World) -> None:
    job = start(world)

    with pytest.raises(ClassroomNotVisibleError):
        world.service.run_job(world.other, world.sec1.id, job.id)

    assert world.client.requests == []


def test_a_cancelled_job_is_never_run(world: World) -> None:
    job = start(world)
    world.service.cancel_job(world.teacher, world.sec1.id, job.id)

    world.service.run_job(world.teacher, world.sec1.id, job.id)

    assert world.client.requests == []


def test_cancelling_mid_run_saves_no_draft_and_charges_nothing(world: World) -> None:
    job = start(world)
    world.client.during_call = lambda: world.service.cancel_job(
        world.teacher, world.sec1.id, job.id
    )

    world.service.run_job(world.teacher, world.sec1.id, job.id)

    assert world.jobs.get(job.id).status is JobStatus.CANCELLED
    assert world.service.drafts(world.teacher, world.sec1.id) == []
    assert world.service.quota(world.teacher).used == 0
    assert world.provider_quota.invalidations == 0


def test_a_late_finish_after_the_job_went_stale_saves_nothing(world: World) -> None:
    job = start(world)
    world.client.during_call = lambda: world.clock.advance(
        STALE_AFTER + timedelta(seconds=1)
    )

    world.service.run_job(world.teacher, world.sec1.id, job.id)

    assert world.service.drafts(world.teacher, world.sec1.id) == []
    assert world.service.quota(world.teacher).used == 0
    assert (
        world.service.job(world.teacher, world.sec1.id, job.id).job.status
        is JobStatus.FAILED
    )


# ---- job (the T-03c read) ---------------------------------------------------


def test_the_owner_reads_the_job(world: World) -> None:
    job = start(world)

    assert world.service.job(world.teacher, world.sec1.id, job.id).job == job


def test_reading_a_stale_job_marks_it_failed_as_a_timeout(world: World) -> None:
    job = start(world)
    world.clock.advance(STALE_AFTER + timedelta(seconds=1))

    seen = world.service.job(world.teacher, world.sec1.id, job.id).job

    assert seen.status is JobStatus.FAILED
    assert seen.error is JobError.TIMEOUT


def test_another_instructor_gets_not_found(world: World) -> None:
    job = start(world)

    with pytest.raises(ClassroomNotVisibleError):
        world.service.job(world.other, world.sec1.id, job.id)


def test_a_member_student_is_forbidden(world: World) -> None:
    job = start(world)

    with pytest.raises(PermissionDeniedError):
        world.service.job(world.student, world.sec1.id, job.id)


def test_a_student_who_is_not_a_member_gets_not_found(world: World) -> None:
    job = start(world)

    with pytest.raises(ClassroomNotVisibleError):
        world.service.job(world.student, world.sec2.id, job.id)


def test_a_job_read_through_another_classrooms_url_gets_not_found(
    world: World,
) -> None:
    job = start(world)

    with pytest.raises(ClassroomNotVisibleError):
        world.service.job(world.teacher, world.sec2.id, job.id)


def test_an_unknown_job_is_gone(world: World) -> None:
    with pytest.raises(GenerationJobGoneError):
        world.service.job(world.teacher, world.sec1.id, 424242)


# ---- cancel_job -------------------------------------------------------------


def test_the_owner_cancels_a_running_job(world: World) -> None:
    job = start(world)

    cancelled = world.service.cancel_job(world.teacher, world.sec1.id, job.id)

    assert cancelled.status is JobStatus.CANCELLED


def test_another_instructor_cannot_cancel(world: World) -> None:
    job = start(world)

    with pytest.raises(ClassroomNotVisibleError):
        world.service.cancel_job(world.other, world.sec1.id, job.id)

    assert world.jobs.get(job.id).status is JobStatus.RUNNING


# ---- provider quota ---------------------------------------------------------


def test_provider_quota_is_the_adapters_snapshot(world: World) -> None:
    assert world.service.provider_quota(world.teacher) == world.provider_quota.current


def test_a_student_cannot_read_the_provider_quota(world: World) -> None:
    with pytest.raises(PermissionDeniedError):
        world.service.provider_quota(world.student)
