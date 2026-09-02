"""Server-rendered routes for the instructor AI workspace."""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from greader.ai.errors import ArtifactReviewError, GenerationError
from greader.ai.review import ArtifactReviewService
from greader.ai.schemas import GenerationMode
from greader.ai.service import AssignmentGenerationService

router = APIRouter(tags=["ai"])


def _assistant_context(
    request: Request,
    *,
    form: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
) -> dict[str, object]:
    """Build the shared template context for the AI composer."""
    return {
        "ai_status": request.app.state.ai_connection_status,
        "assignments": request.app.state.assignment_repo.list_assignments(),
        "form": form
        or {
            "prompt": request.query_params.get("prompt", ""),
            "mode": request.query_params.get("mode", "full_assignment"),
            "assignment_id": request.query_params.get("assignment_id", ""),
        },
        "errors": errors or {},
    }


@router.get("/", response_class=HTMLResponse)
@router.get("/assistant", response_class=HTMLResponse)
async def assistant_page(request: Request) -> HTMLResponse:
    """Render the zero-JavaScript AI assignment composer."""
    return request.app.state.templates.TemplateResponse(
        request,
        "ai/index.html",
        _assistant_context(request),
    )


@router.post("/assistant/generate", response_class=HTMLResponse)
async def generate_artifact(
    request: Request,
    prompt: Annotated[str, Form()] = "",
    mode: Annotated[str, Form()] = GenerationMode.FULL_ASSIGNMENT.value,
    assignment_id: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Generate an artifact and redirect to its server-rendered review page."""
    form = {
        "prompt": prompt,
        "mode": mode,
        "assignment_id": assignment_id,
    }
    try:
        generation_mode = GenerationMode(mode)
    except ValueError:
        return request.app.state.templates.TemplateResponse(
            request,
            "ai/index.html",
            _assistant_context(
                request,
                form=form,
                errors={"form": "Choose a valid generation mode."},
            ),
            status_code=422,
        )

    service = AssignmentGenerationService(
        assignment_repository=request.app.state.assignment_repo,
        generation_repository=request.app.state.generation_repo,
        generator=request.app.state.assignment_generator,
    )
    try:
        artifact = service.generate(
            prompt=prompt,
            mode=generation_mode,
            assignment_id=assignment_id.strip() or None,
        )
    except GenerationError as exc:
        messages = {
            "invalid_prompt": "Enter an instruction before generating.",
            "assignment_required": "Select an existing assignment for this mode.",
            "provider_timeout": "The AI provider timed out. Try again.",
            "provider_authentication_failed": "The AI provider is not configured.",
            "provider_rate_limited": "The AI provider is busy. Try again later.",
            "provider_invalid_response": "The AI provider returned invalid content.",
            "provider_unavailable": "The AI provider is unavailable.",
        }
        error_field = "prompt" if exc.safe_error_code == "invalid_prompt" else "form"
        return request.app.state.templates.TemplateResponse(
            request,
            "ai/index.html",
            _assistant_context(
                request,
                form=form,
                errors={
                    error_field: messages.get(
                        exc.safe_error_code,
                        "Generation failed.",
                    )
                },
            ),
            status_code=422,
        )

    return RedirectResponse(
        url=f"/assistant/artifacts/{artifact.id}",
        status_code=303,
    )


@router.get("/assistant/artifacts/{artifact_id}", response_class=HTMLResponse)
async def artifact_preview(request: Request, artifact_id: str) -> HTMLResponse:
    """Render a persisted generation artifact for instructor review."""
    artifact = request.app.state.generation_repo.get_artifact(artifact_id)
    if artifact is None:
        return request.app.state.templates.TemplateResponse(
            request,
            "ai/not_found.html",
            {"artifact_id": artifact_id},
            status_code=404,
        )
    assignment = (
        request.app.state.assignment_repo.get_assignment(artifact.assignment_id)
        if artifact.assignment_id
        else None
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "ai/artifact.html",
        {
            "artifact": artifact,
            "assignment": assignment,
            "review_error": {
                "artifact_already_applied": "This artifact has already been applied.",
                "artifact_discarded": "A discarded artifact cannot be applied.",
                "no_test_cases_selected": "Select at least one test case.",
                "invalid_test_case_selection": "The selected test cases are invalid.",
                "assignment_not_found": "The target assignment was not found.",
            }.get(request.query_params.get("error", "")),
        },
    )


@router.post("/assistant/artifacts/{artifact_id}/apply")
async def apply_artifact(
    request: Request,
    artifact_id: str,
    selected_indexes: Annotated[list[int] | None, Form()] = None,
) -> RedirectResponse:
    """Apply reviewed content and redirect to the resulting assignment."""
    service = ArtifactReviewService(
        generation_repository=request.app.state.generation_repo
    )
    try:
        result = service.apply_artifact(
            artifact_id,
            selected_indexes=selected_indexes or [],
        )
    except ArtifactReviewError as exc:
        if exc.safe_error_code == "artifact_not_found":
            return RedirectResponse(
                url=f"/assistant/artifacts/{artifact_id}",
                status_code=303,
            )
        return RedirectResponse(
            url=(f"/assistant/artifacts/{artifact_id}?error={exc.safe_error_code}"),
            status_code=303,
        )
    return RedirectResponse(
        url=(
            f"/assignments/{result.assignment_id}"
            f"?saved={result.saved_count}&duplicates={result.duplicate_count}"
        ),
        status_code=303,
    )


@router.post("/assistant/artifacts/{artifact_id}/discard")
async def discard_artifact(request: Request, artifact_id: str) -> RedirectResponse:
    """Discard an artifact and redirect to its retained audit view."""
    service = ArtifactReviewService(
        generation_repository=request.app.state.generation_repo
    )
    try:
        service.discard_artifact(artifact_id)
    except ArtifactReviewError as exc:
        suffix = (
            ""
            if exc.safe_error_code == "artifact_not_found"
            else (f"?error={exc.safe_error_code}")
        )
        return RedirectResponse(
            url=f"/assistant/artifacts/{artifact_id}{suffix}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/assistant/artifacts/{artifact_id}",
        status_code=303,
    )
