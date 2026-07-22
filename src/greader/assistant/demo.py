"""Deterministic demo assignment generator for local use and tests."""

from __future__ import annotations

from greader.assignments.models import Assignment, Difficulty, TestCaseCategory
from greader.assistant.interface import GenerationRequest
from greader.assistant.schemas import (
    FullAssignmentDraft,
    GeneratedExample,
    GeneratedTestCase,
    GenerationMode,
    GenerationResult,
    TestCaseDraftSet,
)


class DemoAssignmentGenerator:
    """Deterministic provider that never contacts an external service."""

    provider_name = "demo"
    model_name = "demo"

    def generate(
        self,
        request: GenerationRequest,
        assignment: Assignment | None,
    ) -> GenerationResult:
        """Return valid structured output for every supported mode."""
        if request.mode is GenerationMode.FULL_ASSIGNMENT:
            payload: FullAssignmentDraft | TestCaseDraftSet = self._full_assignment()
            summary = "Generated demo Python assignment draft."
        elif request.mode is GenerationMode.TEST_CASES:
            payload = self._test_cases(edge_only=False)
            summary = f"Generated demo test cases for {assignment.title}."
        else:
            payload = self._test_cases(edge_only=True)
            summary = f"Generated demo edge cases for {assignment.title}."

        return GenerationResult(
            summary=summary,
            mode=request.mode,
            provider=self.provider_name,
            model_name=self.model_name,
            payload=payload,
        )

    def _full_assignment(self) -> FullAssignmentDraft:
        return FullAssignmentDraft(
            title="Sum Two Integers",
            problem_statement=(
                "Write a Python 3.12 program that reads two integers from standard "
                "input and prints their sum."
            ),
            input_format="One line containing two space-separated integers a and b.",
            output_format="One line containing the integer value of a + b.",
            constraints=[
                "-10^9 <= a <= 10^9",
                "-10^9 <= b <= 10^9",
                "Input always contains exactly two integers.",
            ],
            difficulty=Difficulty.EASY,
            learning_objectives=[
                "Parse space-separated integers from standard input.",
                "Produce exact stdout output for arithmetic expressions.",
            ],
            reference_solution="a, b = map(int, input().split())\nprint(a + b)",
            examples=[
                GeneratedExample(
                    input_data="2 3",
                    expected_output="5",
                    explanation="The two input integers sum to 5.",
                )
            ],
            test_cases=[
                GeneratedTestCase(
                    input_data="2 3",
                    expected_output="5",
                    category=TestCaseCategory.NORMAL,
                    explanation="Small positive integers.",
                ),
                GeneratedTestCase(
                    input_data="-4 9",
                    expected_output="5",
                    category=TestCaseCategory.CORNER,
                    explanation="Mixed-sign input.",
                ),
                GeneratedTestCase(
                    input_data="1000000000 -1000000000",
                    expected_output="0",
                    category=TestCaseCategory.BOUNDARY,
                    explanation="Values at the stated magnitude boundary.",
                ),
            ],
            ambiguity_notes=[
                "This draft assumes the input always contains exactly two integers."
            ],
        )

    def _test_cases(self, *, edge_only: bool) -> TestCaseDraftSet:
        if edge_only:
            return TestCaseDraftSet(
                test_cases=[
                    GeneratedTestCase(
                        input_data="0 0",
                        expected_output="0",
                        category=TestCaseCategory.BOUNDARY,
                        explanation="Both inputs are zero.",
                    ),
                    GeneratedTestCase(
                        input_data="1000000000 1000000000",
                        expected_output="2000000000",
                        category=TestCaseCategory.STRESS,
                        explanation="Largest positive values in the stated range.",
                    ),
                    GeneratedTestCase(
                        input_data="-1000000000 -1000000000",
                        expected_output="-2000000000",
                        category=TestCaseCategory.CORNER,
                        explanation="Largest negative values in the stated range.",
                    ),
                ],
                coverage_notes=["Covers zero and integer magnitude boundaries."],
                ambiguity_notes=[],
            )

        return TestCaseDraftSet(
            test_cases=[
                GeneratedTestCase(
                    input_data="1 4",
                    expected_output="5",
                    category=TestCaseCategory.NORMAL,
                    explanation="Basic addition case.",
                ),
                GeneratedTestCase(
                    input_data="-2 7",
                    expected_output="5",
                    category=TestCaseCategory.CORNER,
                    explanation="Mixed-sign addition case.",
                ),
                GeneratedTestCase(
                    input_data="1000000000 -1",
                    expected_output="999999999",
                    category=TestCaseCategory.BOUNDARY,
                    explanation="Boundary value paired with a small negative value.",
                ),
            ],
            coverage_notes=["Covers normal, mixed-sign, and boundary inputs."],
            ambiguity_notes=[],
        )
