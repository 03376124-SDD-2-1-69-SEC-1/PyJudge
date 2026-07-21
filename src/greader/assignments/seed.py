"""Seed data for the demo assignment repository."""

from greader.assignments.models import (
    Assignment,
    Difficulty,
    ReviewStatus,
    TestCase,
    TestCaseCategory,
)
from greader.assignments.repository import InMemoryAssignmentRepository

_TWO_SUM_ID = "two-sum-optimized"

_TWO_SUM_DESCRIPTION = """\
Given an array of integers `nums` and an integer `target`, return the \
indices of the two numbers such that they add up to `target`.

You may assume that each input would have **exactly one solution**, and \
you may not use the same element twice.

Return the answer in any order.

### Input Format

- Line 1: space-separated integers representing `nums`.
- Line 2: a single integer `target`.

### Output Format

- A single line containing two space-separated indices (0-based)."""

_TWO_SUM_CONSTRAINTS = """\
- 2 ≤ len(nums) ≤ 10⁴
- -10⁹ ≤ nums[i] ≤ 10⁹
- -10⁹ ≤ target ≤ 10⁹
- Exactly one valid answer exists.
- Time complexity must be O(n)."""

_TWO_SUM_REFERENCE = """\
def two_sum(nums: list[int], target: int) -> list[int]:
    seen: dict[int, int] = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []


# Read input
nums = list(map(int, input().split()))
target = int(input())

# Solve and print
result = two_sum(nums, target)
print(result[0], result[1])"""


def _build_test_cases() -> list[TestCase]:
    """Create the eight seed test cases."""
    return [
        TestCase(
            id="tc-01",
            input_data="2 7 11 15\n9",
            expected_output="0 1",
            category=TestCaseCategory.NORMAL,
            status=ReviewStatus.APPROVED,
            explanation="Basic example: 2 + 7 = 9.",
        ),
        TestCase(
            id="tc-02",
            input_data="3 2 4\n6",
            expected_output="1 2",
            category=TestCaseCategory.NORMAL,
            status=ReviewStatus.APPROVED,
            explanation="Avoids using the same element twice (3 + 3 ≠ valid).",
        ),
        TestCase(
            id="tc-03",
            input_data="3 3\n6",
            expected_output="0 1",
            category=TestCaseCategory.BOUNDARY,
            status=ReviewStatus.APPROVED,
            explanation="Minimum-length array with duplicate values.",
        ),
        TestCase(
            id="tc-04",
            input_data="-1 -2 -3 -4 -5\n-8",
            expected_output="2 4",
            category=TestCaseCategory.CORNER,
            status=ReviewStatus.PENDING,
            explanation="All negative numbers; -3 + -5 = -8.",
        ),
        TestCase(
            id="tc-05",
            input_data="0 4 3 0\n0",
            expected_output="0 3",
            category=TestCaseCategory.CORNER,
            status=ReviewStatus.PENDING,
            explanation="Target is zero with duplicate zeros in the array.",
        ),
        TestCase(
            id="tc-06",
            input_data="1000000000 -1000000000 3 4\n0",
            expected_output="0 1",
            category=TestCaseCategory.BOUNDARY,
            status=ReviewStatus.REJECTED,
            explanation="Large magnitude values at the constraint boundary.",
        ),
        TestCase(
            id="tc-07",
            input_data="5 1 9 3 7 2 8 4 6 10\n11",
            expected_output="0 5",
            category=TestCaseCategory.RANDOM,
            status=ReviewStatus.PENDING,
            explanation="Randomised order; 5 + 6 = 11 but checking 5 + 2 pair "
            "triggers hash lookup first at index 5.",
        ),
        TestCase(
            id="tc-08",
            input_data=" ".join(str(i) for i in range(1, 101)) + "\n199",
            expected_output="98 99",
            category=TestCaseCategory.STRESS,
            status=ReviewStatus.REJECTED,
            explanation="Larger input (100 elements). Last two elements sum to 199.",
        ),
    ]


def create_seed_repository() -> InMemoryAssignmentRepository:
    """Build an in-memory repository pre-loaded with the demo assignment."""
    repo = InMemoryAssignmentRepository()

    assignment = Assignment(
        id=_TWO_SUM_ID,
        title="Two Sum Optimized",
        description=_TWO_SUM_DESCRIPTION,
        constraints=_TWO_SUM_CONSTRAINTS,
        difficulty=Difficulty.MEDIUM,
        programming_language="Python",
        status="Draft",
        reference_solution=_TWO_SUM_REFERENCE,
        test_cases=_build_test_cases(),
        ai_suggestions=[
            "Consider adding a test case where the two indices are adjacent "
            "(e.g., indices 0 and 1 with a larger array) to verify the hash "
            "map handles sequential inserts correctly.",
            "Add a test with a single negative and a single positive number "
            "that sum to zero to ensure sign handling is covered.",
            "Include a stress test with 10,000 elements to verify the O(n) "
            "time-complexity requirement under the upper constraint bound.",
        ],
        coverage_score=85.0,
        mutation_score=78.0,
    )

    repo.save_assignment(assignment)
    return repo
