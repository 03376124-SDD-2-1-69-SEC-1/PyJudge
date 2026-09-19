"""FastAPI adapter for the generation endpoint."""

from typing import NoReturn

from fastapi import APIRouter, HTTPException, Request, status

from greader.core.generation.models import GenerationArtifact
from greader.core.generation.schemas import (
    AssignmentDraft,
    Citation,
    GenerationArtifactResponse,
    GenerationRequest,
    TestCaseDraft,
)
from greader.core.generation.service import (
    GenerationArtifactNotFoundError,
    GenerationFailedError,
    GenerationService,
)

router = APIRouter(prefix="/api/v1/generations", tags=["generation"])


def _service(request: Request) -> GenerationService:
    return request.app.state.generation_service


def _raise_artifact_not_found() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "generation_artifact_not_found",
            "message": "Generation artifact not found",
        },
    )


def _raise_generation_failed() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "code": "generation_failed",
            "message": "The generation client failed to produce a draft",
        },
    )


def _response(artifact: GenerationArtifact) -> GenerationArtifactResponse:
    return GenerationArtifactResponse(
        id=artifact.id,
        draft=AssignmentDraft(
            title=artifact.draft.title,
            statement=artifact.draft.statement,
            test_cases=[
                TestCaseDraft(
                    input_data=test_case.input_data,
                    expected_output=test_case.expected_output,
                    is_hidden=test_case.is_hidden,
                    order_index=test_case.order_index,
                )
                for test_case in artifact.draft.test_cases
            ],
        ),
        citations=[
            Citation(
                chunk_id=citation.chunk_id,
                source_id=citation.source_id,
                page=citation.page,
                score=citation.score,
                text_snapshot=citation.text_snapshot,
            )
            for citation in artifact.citations
        ],
        review_status=artifact.review_status,
    )


@router.post(
    "",
    response_model=GenerationArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_generation(
    request: Request,
    payload: GenerationRequest,
) -> GenerationArtifactResponse:
    """Generate an Assignment draft, persist it, and return the stored artifact."""
    try:
        return _response(_service(request).generate(payload))
    except GenerationFailedError:
        _raise_generation_failed()


@router.get("/{artifact_id}", response_model=GenerationArtifactResponse)
def get_generation(artifact_id: int, request: Request) -> GenerationArtifactResponse:
    """Get one stored generation artifact."""
    try:
        return _response(_service(request).get(artifact_id))
    except GenerationArtifactNotFoundError:
        _raise_artifact_not_found()
