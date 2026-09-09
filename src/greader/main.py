"""Application composition for the GReader team scaffold."""

import tempfile
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from greader.ai.app.repository import InMemoryVectorRepository, VectorRepository
from greader.ai.app.routes import router as vector_router
from greader.ai.app.schemas import ApplicationErrorResponse
from greader.ai.app.service import VectorService
from greader.ai.client import StubGenerationClient
from greader.core.generation.repository import GenerationClient
from greader.core.generation.routes import router as generation_router
from greader.core.topics.repository import InMemoryTopicRepository, TopicRepository
from greader.core.topics.routes import router as topic_router
from greader.core.topics.service import TopicService
from greader.database.health import check_db
from greader.database.rag.vector_repository import PostgresVectorRepository
from greader.database.session import get_engine, get_session
from greader.database.storage import (
    R2Storage,
    check_r2,
    get_max_upload_size_bytes,
    get_r2_storage,
    upload_file,
)

_PACKAGE_DIR = Path(__file__).resolve().parent
_WEB_DIR = _PACKAGE_DIR / "web"
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app(
    *,
    topic_repository: TopicRepository | None = None,
    generation_client: GenerationClient | None = None,
    vector_repository: VectorRepository | None = None,
) -> FastAPI:
    """Build an isolated application with server-owned in-memory state."""
    application = FastAPI(
        title="GReader Team Scaffold",
        description="A modular-monolith reference for the GReader team.",
        version="0.1.0",
        responses={422: {"model": ApplicationErrorResponse}},
    )
    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    templates = Jinja2Templates(directory=_TEMPLATE_DIR)
    repository = topic_repository or InMemoryTopicRepository()
    application.state.topic_service = TopicService(repository)
    application.state.vector_service = VectorService(
        vector_repository or InMemoryVectorRepository()
    )
    application.state.generation_client = generation_client or StubGenerationClient()
    application.state.templates = templates
    application.include_router(topic_router)
    application.include_router(vector_router)
    application.include_router(generation_router)

    @application.exception_handler(RequestValidationError)
    def request_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        """Use the application error envelope without echoing submitted values."""
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "request_validation_error",
                    "message": "Request body or parameters are invalid",
                }
            },
        )

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
        storage: R2Storage = Depends(get_r2_storage),  # noqa: B008 — FastAPI DI
    ) -> dict:
        """Confirm the R2 bucket is reachable."""
        try:
            return check_r2(storage)
        except Exception as exc:  # noqa: BLE001 — surface as a 503, not a 500 traceback
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @application.post("/api/v1/uploads")
    def create_upload(
        file: UploadFile,
        storage: R2Storage = Depends(get_r2_storage),  # noqa: B008 — FastAPI DI
    ) -> dict:
        """Store an uploaded file in R2 and return its bucket/key."""
        max_upload_size = get_max_upload_size_bytes()
        contents = file.file.read(max_upload_size + 1)
        if len(contents) > max_upload_size:
            raise HTTPException(status_code=413, detail="File exceeds size limit")

        key = f"uploads/{uuid.uuid4()}-{file.filename}"
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(contents)
            tmp.flush()
            return upload_file(storage, tmp.name, key)

    return application


def create_production_app() -> FastAPI:
    """Select real vector persistence, initializing infrastructure on first use."""
    return create_app(
        vector_repository=PostgresVectorRepository(lambda: Session(get_engine()))
    )


app = create_production_app()
