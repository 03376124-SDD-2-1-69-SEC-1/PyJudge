"""GReader – AI-assisted assignment authoring."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATE_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"


def create_app() -> FastAPI:
    """Application factory."""
    application = FastAPI(title="GReader")

    # Ensure the static directory exists so mounting never fails.
    _STATIC_DIR.mkdir(parents=True, exist_ok=True)
    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    templates = Jinja2Templates(directory=_TEMPLATE_DIR)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @application.get("/health")
    async def health() -> dict:
        """Liveness / readiness probe."""
        return {"status": "ok", "service": "greader"}

    @application.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        """Server-rendered dashboard placeholder."""
        return templates.TemplateResponse(request, "dashboard.html")

    return application


app = create_app()
