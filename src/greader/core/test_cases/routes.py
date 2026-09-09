from fastapi import APIRouter, HTTPException, Request, Response, status

from greader.core.test_cases.models import TestCase
from greader.core.test_cases.schemas import (
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate,
)
from greader.core.test_cases.service import TestCaseNotFoundError, TestCaseService

router = APIRouter(
    prefix="/api/v1/assignments/{assignment_id}/test-cases",
    tags=["Test Cases"],
)


def get_test_case_service(request: Request) -> TestCaseService:
    """Return the application-owned Test Case service."""
    return request.app.state.test_case_service


def _response(test_case: TestCase) -> TestCaseResponse:
    """Convert a Test Case domain object into an HTTP response schema."""
    return TestCaseResponse.model_validate(test_case, from_attributes=True)


def _raise_not_found() -> None:
    """Raise the stable missing-Test-Case HTTP error."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "test_case_not_found", "message": "Test case not found"},
    )


@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_test_case(
    assignment_id: int,
    payload: TestCaseCreate,
    request: Request,
) -> TestCaseResponse:
    """Create a Test Case for an Assignment."""
    return _response(get_test_case_service(request).create_test_case(
        assignment_id=assignment_id,
        input_data=payload.input_data,
        expected_output=payload.expected_output,
        is_hidden=payload.is_hidden,
        order_index=payload.order_index,
    ))


@router.get("", response_model=list[TestCaseResponse])
def list_test_cases(
    assignment_id: int,
    request: Request,
) -> list[TestCaseResponse]:
    """List Test Cases for an Assignment."""
    return [_response(test_case) for test_case in get_test_case_service(request).list_test_cases(assignment_id)]


@router.get("/{test_case_id}", response_model=TestCaseResponse)
def get_test_case(
    assignment_id: int,
    test_case_id: int,
    request: Request,
) -> TestCaseResponse:
    """Get one Test Case."""
    try:
        return _response(get_test_case_service(request).get_test_case(assignment_id, test_case_id))
    except TestCaseNotFoundError:
        _raise_not_found()


@router.put("/{test_case_id}", response_model=TestCaseResponse)
def update_test_case(
    assignment_id: int,
    test_case_id: int,
    payload: TestCaseUpdate,
    request: Request,
) -> TestCaseResponse:
    """Merge supplied fields into a Test Case."""
    try:
        return _response(
            get_test_case_service(request).update_test_case(
                assignment_id=assignment_id,
                test_case_id=test_case_id,
                input_data=payload.input_data,
                expected_output=payload.expected_output,
                is_hidden=payload.is_hidden,
                order_index=payload.order_index,
            )
        )
    except TestCaseNotFoundError:
        _raise_not_found()


@router.delete("/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(
    assignment_id: int,
    test_case_id: int,
    request: Request,
) -> Response:
    """Delete one Test Case."""
    try:
        get_test_case_service(request).delete_test_case(assignment_id, test_case_id)
    except TestCaseNotFoundError:
        _raise_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
