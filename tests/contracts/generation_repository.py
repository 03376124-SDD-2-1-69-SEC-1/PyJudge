"""Contract every GenerationRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/generation/` and to
`SQLGenerationRepository` in `tests/db/`. The round-trip test is the reason
this contract exists: `FakeGenerationRepository` used to hand the submitted
draft/citations back by reference, so it could never catch a bug in the JSON
codec `SQLGenerationRepository` actually uses.
"""

from __future__ import annotations

import pytest

from greader.core.generation.models import AssignmentDraft, Citation, TestCaseDraft
from greader.core.generation.ports import GenerationRepository


def draft(
    title: str = "Sum two numbers",
    statement: str = "Read two ints and print their sum",
    test_cases: list[TestCaseDraft] | None = None,
) -> AssignmentDraft:
    """Return a draft for a contract check to hand to an adapter."""
    return AssignmentDraft(
        title=title,
        statement=statement,
        test_cases=test_cases
        if test_cases is not None
        else [
            TestCaseDraft(
                input_data="1 2", expected_output="3", is_hidden=True, order_index=2
            )
        ],
    )


def citation(
    chunk_id: int = 1,
    source_id: int = 1,
    page: int | None = 3,
    score: float = 0.87,
    text_snapshot: str = "supporting excerpt",
) -> Citation:
    """Return a citation for a contract check to hand to an adapter."""
    return Citation(
        chunk_id=chunk_id,
        source_id=source_id,
        page=page,
        score=score,
        text_snapshot=text_snapshot,
    )


class GenerationRepositoryContract:
    """Checks that hold for any store behind GenerationRepository."""

    def test_create_request_returns_int_id(
        self, repository: GenerationRepository
    ) -> None:
        request_id = repository.create_request("write an assignment", {})

        assert isinstance(request_id, int)

    def test_create_request_twice_returns_different_ids(
        self, repository: GenerationRepository
    ) -> None:
        first = repository.create_request("prompt one", {})
        second = repository.create_request("prompt two", {})

        assert first != second

    def test_mark_request_completed_on_unknown_id_raises_key_error(
        self, repository: GenerationRepository
    ) -> None:
        with pytest.raises(KeyError):
            repository.mark_request_completed(999_999)

    def test_mark_request_failed_on_unknown_id_raises_key_error(
        self, repository: GenerationRepository
    ) -> None:
        with pytest.raises(KeyError):
            repository.mark_request_failed(999_999, error_code="anything")

    def test_create_artifact_returns_entity_with_non_none_int_id(
        self, repository: GenerationRepository
    ) -> None:
        request_id = repository.create_request("prompt", {})

        artifact = repository.create_artifact(request_id, draft(), [citation()])

        assert isinstance(artifact.id, int)

    def test_create_artifact_round_trips_the_draft_and_citations(
        self, repository: GenerationRepository
    ) -> None:
        """Regression test for the codec: two test cases, one nullable page."""
        request_id = repository.create_request("prompt", {})
        submitted_draft = draft(
            test_cases=[
                TestCaseDraft(
                    input_data="1 2", expected_output="3", is_hidden=True, order_index=2
                ),
                TestCaseDraft(
                    input_data="0 0",
                    expected_output="0",
                    is_hidden=False,
                    order_index=0,
                ),
            ]
        )
        submitted_citations = [
            citation(page=None),
            citation(
                chunk_id=2,
                source_id=2,
                page=5,
                score=0.5,
                text_snapshot="another excerpt",
            ),
        ]

        artifact = repository.create_artifact(
            request_id, submitted_draft, submitted_citations
        )

        assert artifact.draft == submitted_draft
        assert artifact.citations == submitted_citations

    def test_get_after_create_artifact_returns_equal_entity(
        self, repository: GenerationRepository
    ) -> None:
        request_id = repository.create_request("prompt", {})
        artifact = repository.create_artifact(request_id, draft(), [citation()])

        fetched = repository.get(artifact.id)

        assert fetched == artifact

    def test_get_on_unknown_id_returns_none(
        self, repository: GenerationRepository
    ) -> None:
        assert repository.get(999_999) is None
