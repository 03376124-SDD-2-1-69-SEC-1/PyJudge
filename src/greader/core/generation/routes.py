"""FastAPI adapter for the generation endpoint."""

from fastapi import APIRouter, Request, status

from greader.core.generation.repository import GenerationClient
from greader.core.generation.schemas import GenerationRequest, GenerationResponse

router = APIRouter(prefix="/api/v1/generations", tags=["generation"])


def _client(request: Request) -> GenerationClient:
    return request.app.state.generation_client


@router.post("", response_model=GenerationResponse, status_code=status.HTTP_201_CREATED)
def create_generation(
    request: Request,
    payload: GenerationRequest,
) -> GenerationResponse:
    """Generate an Assignment draft with supporting citations."""
    return _client(request).generate(payload)
