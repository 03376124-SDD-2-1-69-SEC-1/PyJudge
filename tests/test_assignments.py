"""Tests for the assignment domain, repository, and routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.assignments import (
    Assignment,
    Difficulty,
    InMemoryAssignmentRepository,
    ReviewStatus,
)
from greader.assignments.seed import create_seed_repository
from greader.main import create_app

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def repo() -> InMemoryAssignmentRepository:
    """An empty in-memory repository."""
    return InMemoryAssignmentRepository()


@pytest.fixture()
def seeded_repo() -> InMemoryAssignmentRepository:
    """Repository pre-loaded with seed data."""
    return create_seed_repository()


@pytest.fixture()
def client(seeded_repo):
    """Async test client with seeded assignment data."""
    application = create_app(assignment_repo=seeded_repo)
    transport = ASGITransport(app=application)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ------------------------------------------------------------------
# Repository unit tests
# ------------------------------------------------------------------


class TestInMemoryRepository:
    """Unit tests for InMemoryAssignmentRepository."""

    def test_list_empty(self, repo):
        assert repo.list_assignments() == []

    def test_save_and_get(self, repo):
        assignment = Assignment(
            id="test-1",
            title="Test",
            description="Desc",
            constraints="None",
            difficulty=Difficulty.EASY,
            programming_language="Python",
            status="Draft",
            reference_solution="pass",
        )
        repo.save_assignment(assignment)
        result = repo.get_assignment("test-1")
        assert result is not None
        assert result.title == "Test"

    def test_list_after_save(self, repo):
        assignment = Assignment(
            id="test-1",
            title="Test",
            description="Desc",
            constraints="None",
            difficulty=Difficulty.EASY,
            programming_language="Python",
            status="Draft",
            reference_solution="pass",
        )
        repo.save_assignment(assignment)
        assert len(repo.list_assignments()) == 1

    def test_get_nonexistent_returns_none(self, repo):
        assert repo.get_assignment("does-not-exist") is None

    def test_save_overwrites_existing(self, repo):
        assignment = Assignment(
            id="test-1",
            title="Original",
            description="Desc",
            constraints="None",
            difficulty=Difficulty.EASY,
            programming_language="Python",
            status="Draft",
            reference_solution="pass",
        )
        repo.save_assignment(assignment)

        updated = Assignment(
            id="test-1",
            title="Updated",
            description="Desc",
            constraints="None",
            difficulty=Difficulty.EASY,
            programming_language="Python",
            status="Draft",
            reference_solution="pass",
        )
        repo.save_assignment(updated)

        result = repo.get_assignment("test-1")
        assert result is not None
        assert result.title == "Updated"
        assert len(repo.list_assignments()) == 1


# ------------------------------------------------------------------
# Seed data tests
# ------------------------------------------------------------------


class TestSeedData:
    """Tests that verify the seed repository contents."""

    def test_seed_has_one_assignment(self, seeded_repo):
        assert len(seeded_repo.list_assignments()) == 1

    def test_seed_assignment_is_two_sum(self, seeded_repo):
        assignments = seeded_repo.list_assignments()
        assert assignments[0].title == "Two Sum Optimized"

    def test_seed_difficulty_is_medium(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        assert assignment.difficulty == Difficulty.MEDIUM

    def test_seed_language_is_python(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        assert assignment.programming_language == "Python"

    def test_seed_status_is_draft(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        assert assignment.status == "Draft"

    def test_seed_has_eight_test_cases(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        assert len(assignment.test_cases) == 8

    def test_seed_has_multiple_categories(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        categories = {tc.category for tc in assignment.test_cases}
        assert len(categories) >= 3

    def test_seed_has_mixed_review_statuses(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        statuses = {tc.status for tc in assignment.test_cases}
        assert ReviewStatus.PENDING in statuses
        assert ReviewStatus.APPROVED in statuses
        assert ReviewStatus.REJECTED in statuses

    def test_seed_has_three_ai_suggestions(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        assert len(assignment.ai_suggestions) == 3

    def test_seed_coverage_score(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        assert assignment.coverage_score == 85.0

    def test_seed_mutation_score(self, seeded_repo):
        assignment = seeded_repo.list_assignments()[0]
        assert assignment.mutation_score == 78.0


# ------------------------------------------------------------------
# Route integration tests
# ------------------------------------------------------------------


class TestAssignmentListRoute:
    """Tests for GET /assignments."""

    @pytest.mark.anyio
    async def test_list_returns_200(self, client):
        response = await client.get("/assignments")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_list_returns_html(self, client):
        response = await client.get("/assignments")
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.anyio
    async def test_list_contains_assignment_title(self, client):
        response = await client.get("/assignments")
        assert "Two Sum Optimized" in response.text


class TestAssignmentEditorRoute:
    """Tests for GET /assignments/{assignment_id}."""

    @pytest.mark.anyio
    async def test_editor_returns_200(self, client):
        response = await client.get("/assignments/two-sum-optimized")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_editor_returns_html(self, client):
        response = await client.get("/assignments/two-sum-optimized")
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.anyio
    async def test_editor_shows_title(self, client):
        response = await client.get("/assignments/two-sum-optimized")
        assert "Two Sum Optimized" in response.text

    @pytest.mark.anyio
    async def test_editor_shows_language(self, client):
        response = await client.get("/assignments/two-sum-optimized")
        assert "Python" in response.text

    @pytest.mark.anyio
    async def test_editor_shows_difficulty(self, client):
        response = await client.get("/assignments/two-sum-optimized")
        assert "Medium" in response.text

    @pytest.mark.anyio
    async def test_editor_shows_test_cases(self, client):
        response = await client.get("/assignments/two-sum-optimized")
        # Check that at least one test case input appears
        assert "2 7 11 15" in response.text

    @pytest.mark.anyio
    async def test_unknown_id_returns_404(self, client):
        response = await client.get("/assignments/nonexistent")
        assert response.status_code == 404
