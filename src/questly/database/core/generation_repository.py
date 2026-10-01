"""JSON codecs for the pre-ADR generation artifact shape.

The SQL adapter that used them was removed in OPS-15: the ADR-0007 columns on
`core.generation_requests` (classroom, requester NOT NULL) are ones its port
cannot fill, and Drafts now have their own table (ADR-0008). The codecs stay
because `tests/fakes/generation.py` round-trips through them.
"""

from __future__ import annotations

from questly.core.generation.models import (
    AssignmentDraft,
    Citation,
    TestCaseDraft,
)


def _test_case_to_json(test_case: TestCaseDraft) -> dict[str, object]:
    return {
        "input_data": test_case.input_data,
        "expected_output": test_case.expected_output,
        "is_hidden": test_case.is_hidden,
        "order_index": test_case.order_index,
    }


def _test_case_from_json(data: dict[str, object]) -> TestCaseDraft:
    return TestCaseDraft(
        input_data=str(data["input_data"]),
        expected_output=str(data["expected_output"]),
        is_hidden=bool(data["is_hidden"]),
        order_index=int(data["order_index"]),
    )


def draft_to_json(draft: AssignmentDraft) -> dict[str, object]:
    """Serialize a draft to the JSON shape stored in `generation_artifacts.draft`.

    Public so `tests/fakes/generation.py` can round-trip through the same
    codec the SQL adapter uses, instead of storing the domain object as-is.
    """
    return {
        "title": draft.title,
        "statement": draft.statement,
        "test_cases": [_test_case_to_json(test_case) for test_case in draft.test_cases],
    }


def draft_from_json(data: dict[str, object]) -> AssignmentDraft:
    """Inverse of `draft_to_json`."""
    test_cases = data["test_cases"]
    return AssignmentDraft(
        title=str(data["title"]),
        statement=str(data["statement"]),
        test_cases=[_test_case_from_json(item) for item in test_cases],
    )


def citation_to_json(citation: Citation) -> dict[str, object]:
    """Serialize a citation to the `generation_artifacts.citations` JSON shape.

    Public so `tests/fakes/generation.py` can round-trip through it too.
    """
    return {
        "chunk_id": citation.chunk_id,
        "source_id": citation.source_id,
        "page": citation.page,
        "score": citation.score,
        "text_snapshot": citation.text_snapshot,
    }


def citation_from_json(data: dict[str, object]) -> Citation:
    """Inverse of `citation_to_json`."""
    page = data["page"]
    return Citation(
        chunk_id=int(data["chunk_id"]),
        source_id=int(data["source_id"]),
        page=int(page) if page is not None else None,
        score=float(data["score"]),
        text_snapshot=str(data["text_snapshot"]),
    )
