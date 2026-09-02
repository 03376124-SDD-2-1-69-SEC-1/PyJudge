"""Application composition for the GReader team scaffold."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from greader.core.topics.repository import InMemoryTopicRepository, TopicRepository
from greader.core.topics.routes import router as topic_router
from greader.core.topics.service import TopicService

_PACKAGE_DIR = Path(__file__).resolve().parent
_WEB_DIR = _PACKAGE_DIR / "web"
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app(*, topic_repository: TopicRepository | None = None) -> FastAPI:
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
    application.state.templates = templates
    application.include_router(topic_router)

    @application.get("/")
    def home(request: Request):
        """Render the shared layout example."""
        return templates.TemplateResponse(request, "home.html")

    @application.get("/health")
    def health() -> dict[str, str]:
        """Report application liveness without database dependencies."""
        return {"status": "ok", "service": "greader"}

    return application


app = create_app()
