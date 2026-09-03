"""Application composition for the GReader team scaffold."""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from greader.ai.client import StubGenerationClient
from greader.core.generation.repository import GenerationClient
from greader.core.generation.routes import router as generation_router
from greader.core.topics.repository import InMemoryTopicRepository, TopicRepository
from greader.core.topics.routes import router as topic_router
from greader.core.topics.service import TopicService
from greader.database.health import check_db
from greader.database.session import get_session
from greader.database.storage import check_r2, get_r2_client

_PACKAGE_DIR = Path(__file__).resolve().parent
_WEB_DIR = _PACKAGE_DIR / "web"
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app(
    *,
    topic_repository: TopicRepository | None = None,
    generation_client: GenerationClient | None = None,
) -> FastAPI:
    """Build an isolated application with server-owned in-memory state."""
    application = FastAPI(
        title="GReader Team Scaffold",
        description="A modular-monolith reference for the GReader team.",
        version="0.1.0",
    )
    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    templates = Jinja2Templates(directory=_TEMPLATE_DIR)
    repository = topic_repository or InMemoryTopicRepository()
    application.state.topic_service = TopicService(repository)
    application.state.generation_client = generation_client or StubGenerationClient()
    application.state.templates = templates
    application.include_router(topic_router)
    application.include_router(generation_router)

    @application.get("/")
    def home(request: Request):
        """Render the shared layout example."""
        return templates.TemplateResponse(request, "home.html")

    @application.get("/health")
    def health() -> dict[str, str]:
        """Report application liveness without database dependencies."""
        return {"status": "ok", "service": "greader"}

    @application.get("/health/db")
    def health_db(
        session: Session = Depends(get_session),  # noqa: B008 — FastAPI DI
    ) -> dict:
        """Confirm the Neon connection works and core/rag schemas exist."""
        try:
            return check_db(session)
        except Exception as exc:  # noqa: BLE001 — surface as a 503, not a 500 traceback
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @application.get("/health/r2")
    def health_r2(
        client=Depends(get_r2_client),  # noqa: B008 — FastAPI DI
    ) -> dict:
        """Confirm the R2 bucket is reachable."""
        try:
            return check_r2(client)
        except Exception as exc:  # noqa: BLE001 — surface as a 503, not a 500 traceback
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return application


app = create_app()
