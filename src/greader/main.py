"""Application composition for GReader.

This module builds repositories and services, puts them on `app.state`, includes
the routers, and mounts static files. No business rules live here.

Every repository defaults to its SQL adapter: omit an argument to `create_app`
and the application talks to Postgres, or fails at startup saying which
environment variable is missing. There is no in-memory mode — a test that wants
one passes a fake from `tests/fakes/` explicitly.
"""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from greader.ai.client import StubGenerationClient
from greader.config import Settings, get_settings
from greader.core.assignments.ports import AssignmentRepository
from greader.core.assignments.routes import router as assignment_router
from greader.core.assignments.service import AssignmentService
from greader.core.assignments.testcase_routes import router as test_case_router
from greader.core.generation.ports import GenerationClient
from greader.core.generation.routes import router as generation_router
from greader.core.topics.ports import TopicRepository
from greader.core.topics.routes import router as topic_router
from greader.core.topics.service import TopicService
from greader.core.uploads.ports import KnowledgeDocumentRepository, ObjectStorage
from greader.core.uploads.routes import router as upload_router
from greader.core.uploads.service import UploadService
from greader.database.core.assignment_repository import SQLAssignmentRepository
from greader.database.core.knowledge_document_repository import (
    SQLKnowledgeDocumentRepository,
)
from greader.database.core.topic_repository import SQLTopicRepository
from greader.database.health import check_db
from greader.database.session import (
    SessionFactory,
    build_engine,
    build_session_factory,
    get_session,
)
from greader.database.storage.r2 import R2ObjectStorage, build_r2_client, check_r2

_PACKAGE_DIR = Path(__file__).resolve().parent
_WEB_DIR = _PACKAGE_DIR / "web"
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app(
    *,
    settings: Settings | None = None,
    topic_repository: TopicRepository | None = None,
    assignment_repository: AssignmentRepository | None = None,
    knowledge_document_repository: KnowledgeDocumentRepository | None = None,
    object_storage: ObjectStorage | None = None,
    generation_client: GenerationClient | None = None,
) -> FastAPI:
    """Build the application, wiring SQL adapters for anything not supplied."""
    # Resolved lazily and at most once each, so an app built entirely from
    # injected adapters never reads the environment or opens a connection.
    resolved_settings: list[Settings] = []
    resolved_factory: list[SessionFactory] = []

    def use_settings() -> Settings:
        if settings is not None:
            return settings
        if not resolved_settings:
            resolved_settings.append(get_settings())
        return resolved_settings[0]

    def use_session_factory() -> SessionFactory:
        if not resolved_factory:
            resolved_factory.append(build_session_factory(build_engine(use_settings())))
        return resolved_factory[0]

    application = FastAPI(
        title="GReader",
        description="A modular-monolith service for instructor assignment authoring.",
        version="0.1.0",
    )
    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    templates = Jinja2Templates(directory=_TEMPLATE_DIR)
    application.state.templates = templates

    if topic_repository is None:
        topic_repository = SQLTopicRepository(use_session_factory())
    application.state.topic_service = TopicService(topic_repository)

    if assignment_repository is None:
        assignment_repository = SQLAssignmentRepository(use_session_factory())
    application.state.assignment_service = AssignmentService(assignment_repository)

    if object_storage is None:
        storage_settings = use_settings()
        object_storage = R2ObjectStorage(
            build_r2_client(storage_settings), storage_settings.r2_bucket_name
        )
    if knowledge_document_repository is None:
        knowledge_document_repository = SQLKnowledgeDocumentRepository(
            use_session_factory()
        )
    application.state.upload_service = UploadService(
        object_storage,
        knowledge_document_repository,
        max_upload_size_bytes=use_settings().max_upload_size_bytes,
    )

    if generation_client is None:
        generation_client = StubGenerationClient()
    application.state.generation_client = generation_client

    application.include_router(topic_router)
    application.include_router(assignment_router)
    application.include_router(test_case_router)
    application.include_router(generation_router)
    application.include_router(upload_router)

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
        except Exception as exc:  # noqa: BLE001 — surface as a 503, not a 500
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @application.get("/health/r2")
    def health_r2() -> dict:
        """Confirm the R2 bucket is reachable."""
        bucket_settings = use_settings()
        try:
            return check_r2(
                build_r2_client(bucket_settings), bucket_settings.r2_bucket_name
            )
        except Exception as exc:  # noqa: BLE001 — surface as a 503, not a 500
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return application


def __getattr__(name: str) -> FastAPI:
    """Build the ASGI app the first time `greader.main:app` is resolved.

    `uvicorn greader.main:app` and `fastapi dev` both need a module attribute,
    but building it at import time would make importing this module — which every
    test does — require a populated `.env`.
    """
    if name == "app":
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
