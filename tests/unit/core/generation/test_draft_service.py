"""GenerationService: generate, quota, stepper saves, publish."""

from datetime import timedelta

import pytest

from questly.core.assignments.models import Difficulty, TestCase
from questly.core.auth.models import PermissionDeniedError
from questly.core.generation.models import (
    DraftPart,
    DraftSettings,
    GenerationStep,
)
from questly.core.generation.service import (
    ClassroomNotVisibleError,
    DocumentNotAllowedError,
    DraftNotFoundError,
    GenerationFailedError,
    MissingFieldsError,
    QuotaExceededError,
)
from tests.unit.core.generation.world import DEADLINE, World


def test_generate_creates_a_draft_and_charges_one_quota(world: World) -> None:
    draft = world.generate()

    assert draft.content.title == "Binary search on sorted input"
    assert [tc.kind.value for tc in draft.content.test_cases] == [
        "sample",
        "sample",
        "hidden",
    ]
    assert draft.classroom_ids == [world.sec1.id]
    assert world.service.quota(world.teacher).used == 1
    assert world.client.requests[0].document_ids == [1]


def test_generate_reports_each_step_in_order(world: World) -> None:
    steps: list[GenerationStep] = []

    world.service.generate(
        world.teacher,
        world.sec1.id,
        prompt="Binary search",
        difficulty=Difficulty.MEDIUM,
        on_step=steps.append,
    )

    assert steps == [
        GenerationStep.CALLING_MODEL,
        GenerationStep.VALIDATING,
        GenerationStep.SAVING,
    ]


def test_a_failed_generation_saves_nothing_and_costs_nothing(world: World) -> None:
    world.client.fail = True

    with pytest.raises(GenerationFailedError):
        world.generate()

    assert world.service.quota(world.teacher).used == 0
    assert world.service.drafts(world.teacher, world.sec1.id) == []


def test_quota_is_daily_and_counts_regenerations() -> None:
    world = World(quota=2)
    draft = world.generate()
    world.service.regenerate(world.teacher, draft.id, DraftPart.TITLE)

    with pytest.raises(QuotaExceededError):
        world.generate()
    world.clock.advance(timedelta(days=1))
    assert world.generate().id is not None


def test_generate_checks_classroom_role_and_documents(world: World) -> None:
    with pytest.raises(ClassroomNotVisibleError):
        world.service.generate(
            world.other, world.sec1.id, prompt="x", difficulty=Difficulty.EASY
        )
    with pytest.raises(PermissionDeniedError):
        world.service.generate(
            world.student, world.sec1.id, prompt="x", difficulty=Difficulty.EASY
        )
    with pytest.raises(DocumentNotAllowedError):
        world.service.generate(
            world.teacher,
            world.sec1.id,
            prompt="x",
            difficulty=Difficulty.EASY,
            document_ids=[99],
        )


def test_drafts_belong_to_their_instructor(world: World) -> None:
    draft = world.generate()

    assert [d.id for d in world.service.drafts(world.teacher, world.sec1.id)] == [
        draft.id
    ]
    assert world.service.drafts(world.student, world.sec1.id) == []
    with pytest.raises(DraftNotFoundError):
        world.service.draft(world.other, draft.id)


def test_save_merges_steps_and_missing_fields_guard_next(world: World) -> None:
    draft = world.generate()

    world.service.save(world.teacher, draft.id, title="")
    assert world.service.missing_fields(world.teacher, draft.id, 1) == ["title"]
    assert world.service.missing_fields(world.teacher, draft.id, 3) == ["deadline"]
    saved = world.service.save(
        world.teacher,
        draft.id,
        title="Binary search",
        test_cases=[
            TestCase(input_data="1\n4\n4", expected_output="0"),
            TestCase(input_data="", expected_output=""),
        ],
        settings=DraftSettings(deadline=DEADLINE, max_score=20),
    )

    assert saved.content.problem_statement == draft.content.problem_statement
    assert len(saved.content.test_cases) == 1
    assert world.service.missing_fields(world.teacher, draft.id, 3) == []


def test_publish_needs_every_step_then_posts_to_each_classroom(world: World) -> None:
    draft = world.generate()

    with pytest.raises(MissingFieldsError) as missing:
        world.service.publish(world.teacher, draft.id)
    assert missing.value.fields == ["deadline"]

    world.service.save(
        world.teacher,
        draft.id,
        settings=DraftSettings(deadline=DEADLINE),
        classroom_ids=[world.sec1.id, world.sec2.id],
    )
    published = world.service.publish(world.teacher, draft.id)

    assert [p.classroom_id for p in published.postings] == [
        world.sec1.id,
        world.sec2.id,
    ]
    assert world.service.drafts(world.teacher, world.sec1.id) == []
    assert world.service.published(world.teacher, draft.id).assignment_id == (
        published.assignment.id
    )


def test_publish_targets_are_owned_classrooms_only(world: World) -> None:
    draft = world.generate()

    with pytest.raises(ClassroomNotVisibleError):
        world.service.save(world.teacher, draft.id, classroom_ids=[999])
    targets = world.service.publish_targets(world.teacher)
    assert [(c.id, count) for c, count in targets] == [
        (world.sec1.id, 1),
        (world.sec2.id, 0),
    ]
