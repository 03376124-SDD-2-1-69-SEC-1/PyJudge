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
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from greader.ai.app.repository import VectorRepository
from greader.ai.app.routes import router as vector_router
from greader.ai.app.schemas import ApplicationErrorResponse
from greader.ai.app.service import VectorService
from greader.ai.client import StubGenerationClient
from greader.config import Settings, get_settings
from greader.core.assignments.ports import AssignmentRepository
from greader.core.assignments.routes import router as assignment_router
from greader.core.assignments.service import AssignmentService
from greader.core.assignments.testcase_routes import router as test_case_router
from greader.core.auth.models import NotAuthenticatedError, PermissionDeniedError
from greader.core.auth.pages import DemoAccount
from greader.core.auth.pages import router as auth_page_router
from greader.core.auth.ports import AuthRepository, Clock, VerificationMailer
from greader.core.auth.routes import router as auth_router
from greader.core.auth.service import AuthService
from greader.core.classrooms.pages import router as classroom_page_router
from greader.core.classrooms.ports import ClassroomRepository, ClassroomStats
from greader.core.classrooms.routes import router as classroom_router
from greader.core.classrooms.service import ClassroomService
from greader.core.generation.ports import GenerationClient, GenerationRepository
from greader.core.generation.routes import router as generation_router
from greader.core.generation.service import GenerationService
from greader.core.topics.ports import TopicRepository
from greader.core.topics.routes import router as topic_router
from greader.core.topics.service import TopicService
from greader.core.uploads.ports import KnowledgeDocumentRepository, ObjectStorage
from greader.core.uploads.routes import router as upload_router
from greader.core.uploads.service import UploadService
from greader.database.core.assignment_repository import SQLAssignmentRepository
from greader.database.core.generation_repository import SQLGenerationRepository
from greader.database.core.knowledge_document_repository import (
    SQLKnowledgeDocumentRepository,
)
from greader.database.core.topic_repository import SQLTopicRepository
from greader.database.health import check_db
from greader.database.pending import PendingRepository, SliceNotPersistedError
from greader.database.rag.vector_repository import PostgresVectorRepository
from greader.database.session import (
    SessionFactory,
    build_engine,
    build_session_factory,
    get_session,
)
from greader.database.storage.r2 import R2ObjectStorage, build_r2_client, check_r2
from greader.integrations.clock import SystemClock
from greader.integrations.email import StubEmailSender

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
    generation_repository: GenerationRepository | None = None,
    vector_repository: VectorRepository | None = None,
    auth_repository: AuthRepository | None = None,
    verification_mailer: VerificationMailer | None = None,
    clock: Clock | None = None,
    classroom_repository: ClassroomRepository | None = None,
    classroom_stats: ClassroomStats | None = None,
    demo_accounts: tuple[DemoAccount, ...] | None = None,
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
        responses={422: {"model": ApplicationErrorResponse}},
    )
    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    templates = Jinja2Templates(directory=_TEMPLATE_DIR)
    application.state.templates = templates
    # The "log in as" list on G-01 exists only when scripts/demo.py passes it.
    if demo_accounts is None:
        demo_accounts = ()
    application.state.demo_accounts = demo_accounts

    if clock is None:
        clock = SystemClock()

    # ADR-0007 §10.4: no tables until OPS-15, so production gets a pending
    # adapter that answers every call with 503.
    if auth_repository is None:
        auth_repository = PendingRepository("auth")
    if verification_mailer is None:
        verification_mailer = StubEmailSender()
    auth_service = AuthService(auth_repository, verification_mailer, clock)
    application.state.auth_service = auth_service

    if classroom_repository is None:
        classroom_repository = PendingRepository("classrooms")
    # Card numbers come from assignments and submissions, which have no
    # tables yet either.
    if classroom_stats is None:
        classroom_stats = PendingRepository("classroom stats")
    application.state.classroom_service = ClassroomService(
        classroom_repository, auth_service, classroom_stats, clock
    )

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
    if generation_repository is None:
        generation_repository = SQLGenerationRepository(use_session_factory())
    application.state.generation_service = GenerationService(
        generation_repository, generation_client
    )

    if vector_repository is None:
        vector_repository = PostgresVectorRepository(use_session_factory())
    application.state.vector_service = VectorService(vector_repository)

    application.include_router(topic_router)
    application.include_router(assignment_router)
    application.include_router(test_case_router)
    application.include_router(generation_router)
    application.include_router(upload_router)
    application.include_router(vector_router)
    application.include_router(auth_router)
    application.include_router(auth_page_router)
    application.include_router(classroom_router)
    application.include_router(classroom_page_router)

    @application.exception_handler(NotAuthenticatedError)
    def not_authenticated(request: Request, error: NotAuthenticatedError) -> Response:
        """API callers get 401; a browser on a page is sent to /login."""
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {"code": "not_authenticated", "message": "Log in first"}
                },
            )
        return RedirectResponse("/login", status_code=303)

    @application.exception_handler(PermissionDeniedError)
    def permission_denied(request: Request, error: PermissionDeniedError) -> Response:
        """A member in the wrong role (ADR-0007 §9.6)."""
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=403,
                content={"detail": {"code": "forbidden", "message": "Not allowed"}},
            )
        return HTMLResponse("<h1>403 · Not allowed</h1>", status_code=403)

    @application.exception_handler(SliceNotPersistedError)
    def slice_not_persisted(
        request: Request, error: SliceNotPersistedError
    ) -> Response:
        """A slice whose tables OPS-15 has not created yet."""
        return JSONResponse(
            status_code=503,
            content={"detail": {"code": "not_persisted_yet", "message": str(error)}},
        )

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
