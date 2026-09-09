"""FastAPI adapter for the Assignment API, including its TestCase sub-resource."""

from fastapi import APIRouter, HTTPException, Request, status

from greader.core.assignments.models import Assignment, TestCase
from greader.core.assignments.schemas import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate,
)
from greader.core.assignments.service import (
    AssignmentNotFoundError,
    AssignmentService,
    TestCaseNotFoundError,
)

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


def _test_case_response(test_case: TestCase) -> TestCaseResponse:
    """Convert a domain TestCase into its HTTP response schema."""
    return TestCaseResponse(
        id=test_case.id,
        assignment_id=test_case.assignment_id,
        input_data=test_case.input_data,
        expected_output=test_case.expected_output,
        is_hidden=test_case.is_hidden,
        order_index=test_case.order_index,
    )


def _raise_assignment_not_found() -> None:
    """Raise the stable HTTP representation of a missing Assignment."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "assignment_not_found",
            "message": "Assignment not found",
        },
    )


def _raise_test_case_not_found() -> None:
    """Raise the stable HTTP representation of a missing TestCase."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "test_case_not_found",
            "message": "Test case not found",
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
        _raise_assignment_not_found()


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
        _raise_assignment_not_found()


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, request: Request) -> None:
    """Delete an Assignment."""
    service = get_service(request)
    deleted = service.delete(assignment_id)
    if not deleted:
        _raise_assignment_not_found()


@router.post(
    "/{assignment_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    assignment_id: int, payload: TestCaseCreate, request: Request
) -> TestCaseResponse:
    """Create a TestCase on an Assignment."""
    service = get_service(request)
    try:
        return _test_case_response(
            service.add_test_case(
                assignment_id=assignment_id,
                input_data=payload.input_data,
                expected_output=payload.expected_output,
                is_hidden=payload.is_hidden,
                order_index=payload.order_index,
            )
        )
    except AssignmentNotFoundError:
        _raise_assignment_not_found()


@router.get("/{assignment_id}/test-cases", response_model=list[TestCaseResponse])
def list_test_cases(assignment_id: int, request: Request) -> list[TestCaseResponse]:
    """List every TestCase belonging to an Assignment."""
    service = get_service(request)
    try:
        return [
            _test_case_response(tc) for tc in service.list_test_cases(assignment_id)
        ]
    except AssignmentNotFoundError:
        _raise_assignment_not_found()


@router.get(
    "/{assignment_id}/test-cases/{test_case_id}", response_model=TestCaseResponse
)
def get_test_case(
    assignment_id: int, test_case_id: int, request: Request
) -> TestCaseResponse:
    """Get one TestCase belonging to an Assignment."""
    service = get_service(request)
    try:
        return _test_case_response(service.get_test_case(assignment_id, test_case_id))
    except AssignmentNotFoundError:
        _raise_assignment_not_found()
    except TestCaseNotFoundError:
        _raise_test_case_not_found()


@router.put(
    "/{assignment_id}/test-cases/{test_case_id}", response_model=TestCaseResponse
)
def update_test_case(
    assignment_id: int,
    test_case_id: int,
    payload: TestCaseUpdate,
    request: Request,
) -> TestCaseResponse:
    """Update supplied TestCase fields and retain omitted values."""
    service = get_service(request)
    try:
        return _test_case_response(
            service.update_test_case(
                assignment_id=assignment_id,
                test_case_id=test_case_id,
                input_data=payload.input_data,
                expected_output=payload.expected_output,
                is_hidden=payload.is_hidden,
                order_index=payload.order_index,
            )
        )
    except AssignmentNotFoundError:
        _raise_assignment_not_found()
    except TestCaseNotFoundError:
        _raise_test_case_not_found()


@router.delete(
    "/{assignment_id}/test-cases/{test_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_test_case(assignment_id: int, test_case_id: int, request: Request) -> None:
    """Delete a TestCase belonging to an Assignment."""
    service = get_service(request)
    try:
        deleted = service.delete_test_case(assignment_id, test_case_id)
    except AssignmentNotFoundError:
        _raise_assignment_not_found()
        return
    if not deleted:
        _raise_test_case_not_found()
