"""GReader – AI-assisted assignment authoring."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from greader.assignments.repository import AssignmentRepository
from greader.assignments.routes import router as assignment_router
from greader.assistant.errors import GenerationError
from greader.assistant.interface import AssignmentGenerator
from greader.assistant.providers import ai_connection_status, build_assignment_generator
from greader.assistant.repository import SqlAlchemyGenerationRepository
from greader.assistant.schemas import GenerationMode
from greader.assistant.service import AssignmentGenerationService
from greader.config import Settings
from greader.database import build_session_factory

_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATE_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"


def _default_repositories(
    settings: Settings,
) -> tuple[AssignmentRepository, SqlAlchemyGenerationRepository]:
    """Build the default SQLAlchemy-backed repositories.

    Schema management is handled exclusively by Alembic – this function does
    **not** call ``Base.metadata.create_all()``.
    """
    from greader.assignments.sql_repository import SqlAlchemyAssignmentRepository

    session_factory = build_session_factory(settings.database_url)
    return (
        SqlAlchemyAssignmentRepository(session_factory),
        SqlAlchemyGenerationRepository(session_factory),
    )


def create_app(
    *,
    assignment_repo: AssignmentRepository | None = None,
    generation_repo: SqlAlchemyGenerationRepository | None = None,
    assignment_generator: AssignmentGenerator | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Application factory.

    Parameters
    ----------
    assignment_repo:
        Optional assignment repository for dependency injection.
        Defaults to a SQLAlchemy-backed repository when *None*.
    generation_repo:
        Optional generation repository for dependency injection.
    assignment_generator:
        Optional AI provider for dependency injection.
    settings:
        Optional application settings object.
    """
    settings = settings or Settings()
    application = FastAPI(title="GReader")

    # Ensure the static directory exists so mounting never fails.
    _STATIC_DIR.mkdir(parents=True, exist_ok=True)
    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    templates = Jinja2Templates(directory=_TEMPLATE_DIR)

    # Store shared state for routes to access.
    application.state.templates = templates
    default_assignment_repo: AssignmentRepository | None = None
    default_generation_repo: SqlAlchemyGenerationRepository | None = None
    if assignment_repo is None or generation_repo is None:
        default_assignment_repo, default_generation_repo = _default_repositories(
            settings
        )

    application.state.settings = settings
    application.state.assignment_repo = assignment_repo or default_assignment_repo
    application.state.generation_repo = generation_repo or default_generation_repo
    application.state.assignment_generator = (
        assignment_generator or build_assignment_generator(settings)
    )
    application.state.ai_connection_status = ai_connection_status(settings)

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    application.include_router(assignment_router)

    # ------------------------------------------------------------------
    # Core routes
    # ------------------------------------------------------------------

    @application.get("/health")
    async def health() -> dict:
        """Liveness / readiness probe."""
        return {"status": "ok", "service": "greader"}

    @application.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        """Server-rendered dashboard placeholder."""
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"ai_status": application.state.ai_connection_status},
        )

    @application.post("/assistant/generate")
    async def generate_assignment(request: Request) -> JSONResponse:
        """Generate structured assignment content for the dashboard AI chat."""
        try:
            body = await request.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}

        prompt = body.get("prompt") if isinstance(body.get("prompt"), str) else ""
        assignment_id = (
            body.get("assignment_id")
            if isinstance(body.get("assignment_id"), str)
            and body.get("assignment_id", "").strip()
            else None
        )
        try:
            mode = GenerationMode(body.get("mode") or GenerationMode.FULL_ASSIGNMENT)
        except ValueError:
            return JSONResponse({"error": "invalid_prompt"}, status_code=400)

        service = AssignmentGenerationService(
            assignment_repository=application.state.assignment_repo,
            generation_repository=application.state.generation_repo,
            generator=application.state.assignment_generator,
        )
        try:
            artifact = service.generate(
                prompt=prompt,
                mode=mode,
                assignment_id=assignment_id.strip() if assignment_id else None,
            )
        except GenerationError as exc:
            return JSONResponse({"error": exc.safe_error_code}, status_code=400)

        return JSONResponse(
            {
                "artifact_id": artifact.id,
                "mode": artifact.mode.value,
                "provider": artifact.provider,
                "model_name": artifact.model_name,
                "summary": artifact.summary,
                "payload": artifact.payload.model_dump(mode="json"),
                "created_at": artifact.created_at.isoformat()
                if artifact.created_at
                else None,
            }
        )

    return application


app = create_app()
