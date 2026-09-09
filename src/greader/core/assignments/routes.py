"""FastAPI adapter for the Assignment API."""

from fastapi import APIRouter, HTTPException, Request, status

from greader.core.assignments.models import Assignment
from greader.core.assignments.schemas import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
)
from greader.core.assignments.service import AssignmentNotFoundError, AssignmentService

router = APIRouter(prefix="/api/v1/assignments", tags=["Assignments"])


def get_service(request: Request) -> AssignmentService:
    """Return the application-owned Assignment service."""
    return request.app.state.assignment_service


def _response(assignment: Assignment) -> AssignmentResponse:
    """Convert a domain Assignment into its HTTP response schema."""
    return AssignmentResponse(
        id=assignment.id,
        title=assignment.title,
        problem_statement=assignment.problem_statement,
        difficulty=assignment.difficulty,
        metadata=assignment.metadata,
        artifact_id=assignment.artifact_id,
    )


def _raise_not_found() -> None:
    """Raise the stable HTTP representation of a missing Assignment."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "assignment_not_found",
            "message": "Assignment not found",
        },
    )


@router.get("", response_model=list[AssignmentResponse])
def list_assignments(request: Request) -> list[AssignmentResponse]:
    """List every Assignment."""
    service = get_service(request)
    return [_response(assignment) for assignment in service.list()]


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(assignment_id: int, request: Request) -> AssignmentResponse:
    """Get one Assignment."""
    service = get_service(request)
    try:
        return _response(service.get(assignment_id))
    except AssignmentNotFoundError:
        _raise_not_found()


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate, request: Request
) -> AssignmentResponse:
    """Create an Assignment."""
    service = get_service(request)
    return _response(
        service.create(
            title=payload.title,
            problem_statement=payload.problem_statement,
            difficulty=payload.difficulty,
            metadata=payload.metadata,
        )
    )


@router.put("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    request: Request,
) -> AssignmentResponse:
    """Replace supplied Assignment fields and retain omitted values."""
    service = get_service(request)
    try:
        return _response(
            service.update(
                assignment_id=assignment_id,
                title=payload.title,
                problem_statement=payload.problem_statement,
                difficulty=payload.difficulty,
                metadata=payload.metadata,
            )
        )
    except AssignmentNotFoundError:
        _raise_not_found()


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, request: Request) -> None:
    """Delete an Assignment."""
    service = get_service(request)
    deleted = service.delete(assignment_id)
    if not deleted:
        _raise_not_found()
