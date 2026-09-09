from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from greader.core.test_cases.schemas import (
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate,
)
from greader.core.test_cases.service import TestCaseService

router = APIRouter(
    prefix="/api/v1/assignments/{assignment_id}/test-cases",
    tags=["Test Cases"],
)


def get_test_case_service() -> TestCaseService:
    raise NotImplementedError


ServiceDep = Annotated[TestCaseService, Depends(get_test_case_service)]


@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_test_case(
    assignment_id: int,
    payload: TestCaseCreate,
    service: ServiceDep,
) -> dict[str, Any]:
    return service.create_test_case(
        assignment_id=assignment_id,
        input_data=payload.input_data,
        expected_output=payload.expected_output,
        is_hidden=payload.is_hidden,
        order_index=payload.order_index,
    )


@router.get("", response_model=list[TestCaseResponse])
def list_test_cases(
    assignment_id: int,
    service: ServiceDep,
) -> list[dict[str, Any]]:
    return service.list_test_cases(assignment_id)


@router.get("/{test_case_id}", response_model=TestCaseResponse)
def get_test_case(
    assignment_id: int,
    test_case_id: int,
    service: ServiceDep,
) -> dict[str, Any]:
    tc = service.get_test_case(assignment_id, test_case_id)
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found"
        )
    return tc


@router.put("/{test_case_id}", response_model=TestCaseResponse)
def update_test_case(
    assignment_id: int,
    test_case_id: int,
    payload: TestCaseUpdate,
    service: ServiceDep,
) -> dict[str, Any]:
    tc = service.update_test_case(
        assignment_id=assignment_id,
        test_case_id=test_case_id,
        input_data=payload.input_data,
        expected_output=payload.expected_output,
        is_hidden=payload.is_hidden,
        order_index=payload.order_index,
    )
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found"
        )
    return tc


@router.delete("/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(
    assignment_id: int,
    test_case_id: int,
    service: ServiceDep,
) -> None:
    success = service.delete_test_case(assignment_id, test_case_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found"
        )
