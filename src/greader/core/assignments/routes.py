from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from greader.core.assignments.schemas import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate,
)
from greader.core.assignments.service import AssignmentService

router = APIRouter(prefix="/api/v1/assignments", tags=["Assignments"])


def get_service(request: Request) -> AssignmentService:
    return request.app.state.assignment_service


@router.get("", response_model=list[AssignmentResponse])
def list_assignments(request: Request) -> list[dict[str, Any]]:
    service = get_service(request)
    return service.list_assignments_as_dict()


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(assignment_id: int, request: Request) -> dict[str, Any]:
    service = get_service(request)
    assignment = service.get_assignment_as_dict(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return assignment


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentCreate, request: Request) -> dict[str, Any]:
    service = get_service(request)
    return service.create_assignment_as_dict(
        title=payload.title,
        problem_statement=payload.problem_statement,
        difficulty=payload.difficulty,
        metadata=payload.metadata,
    )


@router.put("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    request: Request,
) -> dict[str, Any]:
    service = get_service(request)
    updated = service.update_assignment_as_dict(
        assignment_id=assignment_id,
        title=payload.title,
        problem_statement=payload.problem_statement,
        difficulty=payload.difficulty,
        metadata=payload.metadata,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return updated


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, request: Request) -> None:
    service = get_service(request)
    deleted = service.delete_assignment(assignment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )


# === Test Cases Endpoints (CORE-05) ===
@router.get("/{assignment_id}/test-cases", response_model=list[TestCaseResponse])
def list_test_cases(assignment_id: int, request: Request) -> list[dict[str, Any]]:
    service = get_service(request)
    test_cases = service.list_test_cases_as_dict(assignment_id)
    if test_cases is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    return test_cases


@router.post(
    "/{assignment_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    assignment_id: int, payload: TestCaseCreate, request: Request
) -> dict[str, Any]:
    service = get_service(request)
    created = service.create_test_case_as_dict(
        assignment_id=assignment_id,
        input_data=payload.input_data,
        expected_output=payload.expected_output,
        is_hidden=payload.is_hidden,
        weight=payload.weight,
    )
    if not created:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    return created


@router.put(
    "/{assignment_id}/test-cases/{test_case_id}",
    response_model=TestCaseResponse,
)
def update_test_case(
    assignment_id: int,
    test_case_id: int,
    payload: TestCaseUpdate,
    request: Request,
) -> dict[str, Any]:
    service = get_service(request)
    updated = service.update_test_case_as_dict(
        assignment_id=assignment_id,
        test_case_id=test_case_id,
        input_data=payload.input_data,
        expected_output=payload.expected_output,
        is_hidden=payload.is_hidden,
        weight=payload.weight,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment or TestCase not found",
        )
    return updated


@router.delete(
    "/{assignment_id}/test-cases/{test_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_test_case(assignment_id: int, test_case_id: int, request: Request) -> None:
    service = get_service(request)
    if not service.delete_test_case(assignment_id, test_case_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment or TestCase not found",
        )
