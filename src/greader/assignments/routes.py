"""Assignment routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from greader.assignments.repository import AssignmentRepository

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _get_repo(request: Request) -> AssignmentRepository:
    """Retrieve the assignment repository from app state."""
    return request.app.state.assignment_repo


def _get_templates(request: Request) -> Jinja2Templates:
    """Retrieve the Jinja2 templates from app state."""
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_assignments(request: Request) -> HTMLResponse:
    """List all available assignments."""
    repo = _get_repo(request)
    templates = _get_templates(request)
    assignments = repo.list_assignments()
    return templates.TemplateResponse(
        request,
        "assignments/index.html",
        {"assignments": assignments},
    )


@router.get("/{assignment_id}", response_class=HTMLResponse)
async def assignment_editor(request: Request, assignment_id: str) -> HTMLResponse:
    """Render the instructor editor for a single assignment."""
    repo = _get_repo(request)
    templates = _get_templates(request)
    assignment = repo.get_assignment(assignment_id)
    if assignment is None:
        return templates.TemplateResponse(
            request,
            "assignments/not_found.html",
            {"assignment_id": assignment_id},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "assignments/editor.html",
        {"assignment": assignment},
    )
