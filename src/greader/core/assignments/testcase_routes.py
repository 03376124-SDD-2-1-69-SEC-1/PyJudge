"""FastAPI adapter for the TestCase sub-resource of an Assignment.

A separate router from `routes.py` so neither file mixes two resources; the
domain stays one aggregate (CORE-11) and both routers share one service.

Named `testcase_routes.py`, not `test_case_routes.py`: the architecture test that
keeps pytest files out of `src/` matches any filename starting with `test_`.
"""

from typing import NoReturn

from fastapi import APIRouter, HTTPException, Request, Response, status

from greader.core.assignments.models import TestCase
from greader.core.assignments.routes import get_service, raise_assignment_not_found
from greader.core.assignments.schemas import (
    TestCaseCreate,
    TestCasePatch,
    TestCaseReplace,
    TestCaseResponse,
)
from greader.core.assignments.service import (
    AssignmentNotFoundError,
    TestCaseNotFoundError,
)

router = APIRouter(
    prefix="/api/v1/assignments/{assignment_id}/test-cases",
    tags=["Assignments"],
)


def _response(test_case: TestCase) -> TestCaseResponse:
    """Convert a domain TestCase into its HTTP response schema."""
    return TestCaseResponse(
        id=test_case.id,
        input_data=test_case.input_data,
        expected_output=test_case.expected_output,
        is_hidden=test_case.is_hidden,
        order_index=test_case.order_index,
    )


def _raise_test_case_not_found() -> NoReturn:
    """Raise the stable HTTP representation of a missing TestCase."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "test_case_not_found",
            "message": "Test case not found",
        },
    )


@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_test_case(
    assignment_id: int, payload: TestCaseCreate, request: Request
) -> TestCaseResponse:
    """Create a TestCase on an Assignment."""
    service = get_service(request)
    try:
        return _response(
            service.add_test_case(
                assignment_id=assignment_id,
                input_data=payload.input_data,
                expected_output=payload.expected_output,
                is_hidden=payload.is_hidden,
                order_index=payload.order_index,
            )
        )
    except AssignmentNotFoundError:
        raise_assignment_not_found()


@router.get("", response_model=list[TestCaseResponse])
def list_test_cases(assignment_id: int, request: Request) -> list[TestCaseResponse]:
    """List every TestCase belonging to an Assignment."""
    service = get_service(request)
    try:
        return [_response(tc) for tc in service.list_test_cases(assignment_id)]
    except AssignmentNotFoundError:
        raise_assignment_not_found()


@router.get("/{test_case_id}", response_model=TestCaseResponse)
def get_test_case(
    assignment_id: int, test_case_id: int, request: Request
) -> TestCaseResponse:
    """Get one TestCase belonging to an Assignment."""
    service = get_service(request)
    try:
        return _response(service.get_test_case(assignment_id, test_case_id))
    except AssignmentNotFoundError:
        raise_assignment_not_found()
    except TestCaseNotFoundError:
        _raise_test_case_not_found()


@router.put("/{test_case_id}", response_model=TestCaseResponse)
def replace_test_case(
    assignment_id: int,
    test_case_id: int,
    payload: TestCaseReplace,
    request: Request,
) -> TestCaseResponse:
    """Replace every client-writable field of a TestCase."""
    service = get_service(request)
    try:
        return _response(
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
        raise_assignment_not_found()
    except TestCaseNotFoundError:
        _raise_test_case_not_found()


@router.patch("/{test_case_id}", response_model=TestCaseResponse)
def patch_test_case(
    assignment_id: int,
    test_case_id: int,
    payload: TestCasePatch,
    request: Request,
) -> TestCaseResponse:
    """Update only the TestCase fields present in the request body."""
    service = get_service(request)
    try:
        return _response(
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
        raise_assignment_not_found()
    except TestCaseNotFoundError:
        _raise_test_case_not_found()


@router.delete("/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(
    assignment_id: int, test_case_id: int, request: Request
) -> Response:
    """Delete a TestCase belonging to an Assignment."""
    service = get_service(request)
    try:
        service.delete_test_case(assignment_id, test_case_id)
    except AssignmentNotFoundError:
        raise_assignment_not_found()
    except TestCaseNotFoundError:
        _raise_test_case_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
