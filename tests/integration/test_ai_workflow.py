"""End-to-end HTTP tests for the server-rendered AI workflow."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.ai.demo import DemoAssignmentGenerator
from greader.ai.repository import SqlAlchemyGenerationRepository
from greader.assignments.models import (
    Assignment,
    Difficulty,
    ReviewStatus,
    TestCase,
    TestCaseCategory,
)
from greader.assignments.sql_repository import SqlAlchemyAssignmentRepository
from greader.main import create_app


def _application(test_session_factory):
    return create_app(
        assignment_repo=SqlAlchemyAssignmentRepository(test_session_factory),
        generation_repo=SqlAlchemyGenerationRepository(test_session_factory),
        assignment_generator=DemoAssignmentGenerator(),
    )


class _HtmlTextGenerator(DemoAssignmentGenerator):
    def generate(self, request, assignment):
        result = super().generate(request, assignment)
        payload = result.payload.model_copy(
            update={
                "problem_statement": (
                    "Write a sufficiently detailed programming exercise. "
                    "<script>alert('unsafe')</script>"
                )
            }
        )
        return result.model_copy(update={"payload": payload})


async def _generate(
    client: AsyncClient,
    *,
    mode: str = "full_assignment",
    assignment_id: str = "",
):
    return await client.post(
        "/assistant/generate",
        data={
            "prompt": "Generate reviewed assignment material.",
            "mode": mode,
            "assignment_id": assignment_id,
        },
    )


@pytest.mark.anyio
async def test_successful_generation_redirects_to_server_rendered_artifact(
    test_session_factory,
) -> None:
    application = _application(test_session_factory)
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/assistant/generate",
            data={
                "prompt": "Create a small arithmetic assignment.",
                "mode": "full_assignment",
                "assignment_id": "",
            },
        )

        assert response.status_code == 303
        assert response.headers["location"].startswith("/assistant/artifacts/")

        preview = await client.get(response.headers["location"])

    assert preview.status_code == 200
    assert "Sum Two Integers" in preview.text
    assert "Examples" in preview.text
    assert "Ambiguity notes" in preview.text
    assert "Generated at" in preview.text
    assert "Save as Draft Assignment" in preview.text
    assert "<script" not in preview.text.lower()


@pytest.mark.anyio
async def test_invalid_prompt_is_preserved_by_server_rendered_validation(
    test_session_factory,
) -> None:
    application = _application(test_session_factory)
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/assistant/generate",
            data={
                "prompt": "   ",
                "mode": "full_assignment",
                "assignment_id": "",
            },
        )

    assert response.status_code == 422
    assert 'name="prompt"' in response.text
    assert "Enter an instruction before generating." in response.text


@pytest.mark.anyio
async def test_applying_full_artifact_redirects_to_persisted_assignment(
    test_session_factory,
) -> None:
    application = _application(test_session_factory)
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        generated = await _generate(client)
        applied = await client.post(f"{generated.headers['location']}/apply")

        assert applied.status_code == 303
        assert applied.headers["location"].startswith("/assignments/")

        assignment = await client.get(applied.headers["location"])

    assert assignment.status_code == 200
    assert "Sum Two Integers" in assignment.text
    assert "Pending" in assignment.text


@pytest.mark.anyio
async def test_discarding_artifact_redirects_to_read_only_review(
    test_session_factory,
) -> None:
    application = _application(test_session_factory)
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        generated = await _generate(client)
        discarded = await client.post(f"{generated.headers['location']}/discard")
        preview = await client.get(discarded.headers["location"])

    assert discarded.status_code == 303
    assert preview.status_code == 200
    assert "Discarded" in preview.text
    assert "Save as Draft Assignment" not in preview.text


@pytest.mark.anyio
async def test_test_case_preview_requires_selection_before_apply(
    test_session_factory,
) -> None:
    assignments = SqlAlchemyAssignmentRepository(test_session_factory)
    assignments.save_assignment(
        Assignment(
            id="assignment-1",
            title="Sum Two Numbers",
            description="Read two integers and print their sum.",
            constraints="Two integers.",
            difficulty=Difficulty.EASY,
            programming_language="Python",
            status="Draft",
            reference_solution="a, b = map(int, input().split())\nprint(a + b)",
        )
    )
    application = create_app(
        assignment_repo=assignments,
        generation_repo=SqlAlchemyGenerationRepository(test_session_factory),
        assignment_generator=DemoAssignmentGenerator(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        generated = await _generate(
            client,
            mode="test_cases",
            assignment_id="assignment-1",
        )
        preview = await client.get(generated.headers["location"])
        rejected = await client.post(f"{generated.headers['location']}/apply")
        error_page = await client.get(rejected.headers["location"])

    assert preview.status_code == 200
    assert 'name="selected_indexes"' in preview.text
    assert rejected.status_code == 303
    assert "Select at least one test case." in error_page.text


@pytest.mark.anyio
async def test_saved_test_case_page_reports_duplicates(test_session_factory) -> None:
    assignments = SqlAlchemyAssignmentRepository(test_session_factory)
    assignments.save_assignment(
        Assignment(
            id="assignment-1",
            title="Sum Two Numbers",
            description="Read two integers and print their sum.",
            constraints="Two integers.",
            difficulty=Difficulty.EASY,
            programming_language="Python",
            status="Draft",
            reference_solution="a, b = map(int, input().split())\nprint(a + b)",
            test_cases=[
                TestCase(
                    id="existing",
                    assignment_id="assignment-1",
                    input_data="1 4  \r\n",
                    expected_output="5  \r\n\r\n",
                    category=TestCaseCategory.NORMAL,
                    status=ReviewStatus.APPROVED,
                    explanation="Existing case.",
                )
            ],
        )
    )
    application = create_app(
        assignment_repo=assignments,
        generation_repo=SqlAlchemyGenerationRepository(test_session_factory),
        assignment_generator=DemoAssignmentGenerator(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        generated = await _generate(
            client,
            mode="test_cases",
            assignment_id="assignment-1",
        )
        applied = await client.post(
            f"{generated.headers['location']}/apply",
            data={"selected_indexes": ["0", "1"]},
        )
        assignment = await client.get(applied.headers["location"])

    assert applied.status_code == 303
    assert "1 test case saved" in assignment.text
    assert "1 duplicate skipped" in assignment.text


@pytest.mark.anyio
async def test_generated_html_is_escaped_without_creating_script_tags(
    test_session_factory,
) -> None:
    application = create_app(
        assignment_repo=SqlAlchemyAssignmentRepository(test_session_factory),
        generation_repo=SqlAlchemyGenerationRepository(test_session_factory),
        assignment_generator=_HtmlTextGenerator(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        generated = await _generate(client)
        preview = await client.get(generated.headers["location"])

    assert "<script" not in preview.text.lower()
    assert "&lt;script&gt;" in preview.text
