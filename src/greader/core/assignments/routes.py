"""FastAPI adapter for the Assignment API.

The TestCase sub-resource has its own router in `test_case_routes.py`; both are
mounted by `main.py`. `get_service` and `raise_assignment_not_found` are shared
with that module, which is why they carry no leading underscore.
"""

from typing import NoReturn

from fastapi import APIRouter, HTTPException, Request, Response, status

from greader.core.assignments.models import Assignment
from greader.core.assignments.schemas import (
    AssignmentCreate,
    AssignmentPatch,
    AssignmentReplace,
    AssignmentResponse,
)
from greader.core.assignments.service import (
    AssignmentNotFoundError,
    AssignmentService,
)

router = APIRouter(prefix="/api/v1/assignments", tags=["Assignments"])


def get_service(request: Request) -> AssignmentService:
    """Return the application-owned Assignment service."""
    return request.app.state.assignment_service


def raise_assignment_not_found() -> NoReturn:
    """Raise the stable HTTP representation of a missing Assignment."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "assignment_not_found",
            "message": "Assignment not found",
        },
    )


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
        raise_assignment_not_found()


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
def replace_assignment(
    assignment_id: int,
    payload: AssignmentReplace,
    request: Request,
) -> AssignmentResponse:
    """Replace every client-writable field of an Assignment."""
    service = get_service(request)
    try:
        return _response(
            service.replace(
                assignment_id=assignment_id,
                title=payload.title,
                problem_statement=payload.problem_statement,
                difficulty=payload.difficulty,
                metadata=payload.metadata,
            )
        )
    except AssignmentNotFoundError:
        raise_assignment_not_found()


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
def patch_assignment(
    assignment_id: int,
    payload: AssignmentPatch,
    request: Request,
) -> AssignmentResponse:
    """Update only the fields present in the request body."""
    service = get_service(request)
    try:
        return _response(
            service.patch(
                assignment_id=assignment_id,
                title=payload.title,
                problem_statement=payload.problem_statement,
                difficulty=payload.difficulty,
                metadata=payload.metadata,
            )
        )
    except AssignmentNotFoundError:
        raise_assignment_not_found()


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, request: Request) -> Response:
    """Delete an Assignment."""
    service = get_service(request)
    try:
        service.delete(assignment_id)
    except AssignmentNotFoundError:
        raise_assignment_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
