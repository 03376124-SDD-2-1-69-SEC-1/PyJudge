"""Application composition for Questly.

This module builds repositories and services, puts them on `app.state`, includes
the routers, and mounts static files. No business rules live here.

Every repository defaults to its SQL adapter: omit an argument to `create_app`
and the application talks to Postgres, or fails at startup saying which
environment variable is missing. There is no in-memory mode — a test that wants
one passes a fake from `tests/fakes/` explicitly.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from questly.ai.app.repository import VectorRepository
from questly.ai.app.routes import router as vector_router
from questly.ai.app.schemas import ApplicationErrorResponse
from questly.ai.app.service import VectorService
from questly.ai.client import OpenRouterGenerationClient, StubGenerationClient
from questly.config import Settings, get_settings
from questly.core.admin.ports import AdminRepository, SystemHealthChecker
from questly.core.admin.routes import router as admin_router
from questly.core.admin.service import AdminService
from questly.core.assignments.ports import (
    AssignmentRepository,
    PostingRepository,
    PostingStats,
    VersionRepository,
)
from questly.core.assignments.routes import (
    classroom_router as assignment_classroom_router,
)
from questly.core.assignments.routes import router as assignment_router
from questly.core.assignments.service import AssignmentService
from questly.core.assignments.testcase_routes import router as test_case_router
from questly.core.auth.csrf import csrf_token
from questly.core.auth.models import (
    CsrfTokenError,
    NotAuthenticatedError,
    PermissionDeniedError,
)
from questly.core.auth.pages import DemoAccount
from questly.core.auth.pages import router as auth_page_router
from questly.core.auth.ports import AuthRepository, Clock, VerificationMailer
from questly.core.auth.routes import router as auth_router
from questly.core.auth.service import AuthService
from questly.core.classrooms.pages import router as classroom_page_router
from questly.core.classrooms.ports import ClassroomRepository, ClassroomStats
from questly.core.classrooms.routes import router as classroom_router
from questly.core.classrooms.service import ClassroomService
from questly.core.classrooms.stats import ComputedClassroomStats
from questly.core.generation.pages import router as generation_page_router
from questly.core.generation.ports import (
    DocumentCatalog,
    DraftRepository,
    GenerationClient,
)
from questly.core.generation.routes import classroom_router as draft_classroom_router
from questly.core.generation.routes import router as draft_router
from questly.core.generation.service import GenerationService
from questly.core.submissions.pages import router as submission_page_router
from questly.core.submissions.ports import CodeRunner, SubmissionRepository
from questly.core.submissions.routes import (
    classroom_router as submission_classroom_router,
)
from questly.core.submissions.routes import router as submission_router
from questly.core.submissions.service import SubmissionService
from questly.core.submissions.stats import SubmissionPostingStats
from questly.core.topics.ports import TopicRepository
from questly.core.topics.routes import router as topic_router
from questly.core.topics.service import TopicService
from questly.core.uploads.ports import KnowledgeDocumentRepository, ObjectStorage
from questly.core.uploads.routes import router as upload_router
from questly.core.uploads.service import UploadService
from questly.database.core.admin_repository import SQLAdminRepository
from questly.database.core.assignment_repository import SQLAssignmentRepository
from questly.database.core.auth_repository import SQLAuthRepository
from questly.database.core.classroom_repository import SQLClassroomRepository
from questly.database.core.document_catalog_repository import SQLDocumentCatalog
from questly.database.core.draft_repository import SQLDraftRepository
from questly.database.core.knowledge_document_repository import (
    SQLKnowledgeDocumentRepository,
)
from questly.database.core.posting_repository import SQLPostingRepository
from questly.database.core.submission_repository import SQLSubmissionRepository
from questly.database.core.topic_repository import SQLTopicRepository
from questly.database.core.version_repository import SQLVersionRepository
from questly.database.health import SQLSystemHealthChecker, check_db
from questly.database.rag.vector_repository import PostgresVectorRepository
from questly.database.session import (
    SessionFactory,
    build_engine,
    build_session_factory,
    get_session,
)
from questly.database.storage.r2 import R2ObjectStorage, build_r2_client, check_r2
from questly.integrations.clock import SystemClock
from questly.integrations.email import StubEmailSender
from questly.integrations.judge0 import StubCodeRunner

_PACKAGE_DIR = Path(__file__).resolve().parent
_WEB_DIR = _PACKAGE_DIR / "web"
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


DISPLAY_ZONE = ZoneInfo("Asia/Bangkok")


def local_time(value: datetime, pattern: str = "%-d %b, %H:%M") -> str:
    """Render a stored UTC time in Bangkok time for templates (`|local`)."""
    local_value = value.astimezone(DISPLAY_ZONE)
    day_placeholder = "\x00LOCAL_TIME_DAY\x00"
    portable_pattern = pattern.replace("%-d", day_placeholder)
    return local_value.strftime(portable_pattern).replace(
        day_placeholder, str(local_value.day)
    )


def asset_url(path: str) -> str:
    """Return `/static/<path>?v=<mtime>` so a rebuilt file gets a new URL.

    StaticFiles sends no Cache-Control, so browsers cache app.css heuristically
    from Last-Modified and can keep an old build for days, even across a
    reload. The version changes whenever the file on disk changes, including
    a `tailwindcss --watch` rebuild while the server keeps running.
    """
    version = int((_STATIC_DIR / path).stat().st_mtime)
    return f"/static/{path}?v={version}"


def create_app(
    *,
    settings: Settings | None = None,
    topic_repository: TopicRepository | None = None,
    assignment_repository: AssignmentRepository | None = None,
    version_repository: VersionRepository | None = None,
    posting_repository: PostingRepository | None = None,
    posting_stats: PostingStats | None = None,
    knowledge_document_repository: KnowledgeDocumentRepository | None = None,
    object_storage: ObjectStorage | None = None,
    generation_client: GenerationClient | None = None,
    draft_repository: DraftRepository | None = None,
    document_catalog: DocumentCatalog | None = None,
    vector_repository: VectorRepository | None = None,
    auth_repository: AuthRepository | None = None,
    admin_repository: AdminRepository | None = None,
    system_health_checker: SystemHealthChecker | None = None,
    verification_mailer: VerificationMailer | None = None,
    clock: Clock | None = None,
    classroom_repository: ClassroomRepository | None = None,
    classroom_stats: ClassroomStats | None = None,
    submission_repository: SubmissionRepository | None = None,
    code_runner: CodeRunner | None = None,
    demo_accounts: tuple[DemoAccount, ...] | None = None,
    secure_cookies: bool | None = None,
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
        title="Questly",
        description="A modular-monolith service for instructor assignment authoring.",
        version="0.1.0",
        responses={422: {"model": ApplicationErrorResponse}},
    )
    application.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    templates = Jinja2Templates(directory=_TEMPLATE_DIR)
    templates.env.globals["asset_url"] = asset_url
    templates.env.globals["csrf_token"] = csrf_token
    templates.env.filters["local"] = local_time
    application.state.templates = templates
    # The "log in as" list on G-01 exists only when scripts/demo.py passes it.
    if demo_accounts is None:
        demo_accounts = ()
    application.state.demo_accounts = demo_accounts
    # Cookies are Secure unless a caller on plain HTTP (scripts/demo.py, the
    # tests) turns it off explicitly.
    if secure_cookies is None:
        secure_cookies = True
    application.state.secure_cookies = secure_cookies

    if clock is None:
        clock = SystemClock()

    # Every classroom slice persists to Postgres (OPS-15); a caller may inject
    # any adapter instead, as the tests and scripts/demo.py do. Repositories
    # are resolved before the services because ClassroomStats reads four of
    # them.
    if auth_repository is None:
        auth_repository = SQLAuthRepository(use_session_factory())
    if classroom_repository is None:
        classroom_repository = SQLClassroomRepository(use_session_factory())
    if assignment_repository is None:
        assignment_repository = SQLAssignmentRepository(use_session_factory())
    if version_repository is None:
        version_repository = SQLVersionRepository(use_session_factory())
    if posting_repository is None:
        posting_repository = SQLPostingRepository(use_session_factory())
    if submission_repository is None:
        submission_repository = SQLSubmissionRepository(use_session_factory())
    if draft_repository is None:
        draft_repository = SQLDraftRepository(use_session_factory())
    if document_catalog is None:
        document_catalog = SQLDocumentCatalog(use_session_factory())
    if classroom_stats is None:
        classroom_stats = ComputedClassroomStats(
            posting_repository,
            submission_repository,
            classroom_repository,
            draft_repository,
            clock,
        )

    if verification_mailer is None:
        verification_mailer = StubEmailSender()
    if admin_repository is None:
        admin_repository = SQLAdminRepository(use_session_factory())
    if system_health_checker is None:
        system_health_checker = SQLSystemHealthChecker(
            use_session_factory(),
            generation_available=(
                bool(use_settings().openrouter_api_key)
                or (
                    generation_client is not None
                    and not isinstance(generation_client, StubGenerationClient)
                )
            ),
            sandbox_available=(
                code_runner is not None and not isinstance(code_runner, StubCodeRunner)
            ),
            email_available=(
                verification_mailer is not None
                and not isinstance(verification_mailer, StubEmailSender)
            ),
        )
    auth_service = AuthService(auth_repository, verification_mailer, clock)
    application.state.auth_service = auth_service
    admin_service = AdminService(
        admin_repository,
        auth_repository,
        system_health_checker,
        allowed_models=(use_settings().generation_model,),
    )
    application.state.admin_service = admin_service

    def get_daily_quota() -> int:
        if admin_repository is None:
            raise RuntimeError("AdminRepository is not wired; see paired OPS-22")
        return admin_repository.get_ai_settings().daily_quota

    classroom_service = ClassroomService(
        classroom_repository, auth_service, classroom_stats, clock
    )
    application.state.classroom_service = classroom_service

    # T-01/S-01 numbers are computed from Submissions unless a test injects its
    # own PostingStats.
    if posting_stats is None:
        posting_stats = SubmissionPostingStats(
            submission_repository, assignment_repository
        )
    assignment_service = AssignmentService(
        assignment_repository,
        version_repository,
        posting_repository,
        classroom_service,
        posting_stats,
        clock,
    )
    application.state.assignment_service = assignment_service

    if code_runner is None:
        code_runner = StubCodeRunner()
    application.state.submission_service = SubmissionService(
        submission_repository, code_runner, assignment_service, classroom_service, clock
    )

    if generation_client is None:
        if use_settings().openrouter_api_key:
            generation_client = OpenRouterGenerationClient(
                api_key=use_settings().openrouter_api_key,
                model=use_settings().generation_model,
                code_runner=code_runner,
            )
        else:
            generation_client = StubGenerationClient()
    application.state.generation_service = GenerationService(
        draft_repository,
        generation_client,
        document_catalog,
        classroom_service,
        assignment_service,
        clock,
        daily_quota=get_daily_quota,
    )

    if topic_repository is None:
        topic_repository = SQLTopicRepository(use_session_factory())
    application.state.topic_service = TopicService(topic_repository)

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

    if vector_repository is None:
        vector_repository = PostgresVectorRepository(use_session_factory())
    application.state.vector_service = VectorService(vector_repository)

    application.include_router(topic_router)
    application.include_router(assignment_router)
    application.include_router(assignment_classroom_router)
    application.include_router(test_case_router)
    application.include_router(draft_router)
    application.include_router(draft_classroom_router)
    application.include_router(generation_page_router)
    application.include_router(upload_router)
    application.include_router(vector_router)
    application.include_router(auth_router)
    application.include_router(auth_page_router)
    application.include_router(admin_router)
    application.include_router(classroom_router)
    application.include_router(classroom_page_router)
    application.include_router(submission_router)
    application.include_router(submission_classroom_router)
    application.include_router(submission_page_router)

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

    @application.exception_handler(CsrfTokenError)
    def csrf_rejected(request: Request, error: CsrfTokenError) -> Response:
        """A form posted without its page's token (core/auth/csrf.py)."""
        return HTMLResponse(
            "<h1>403 · This form expired</h1><p>Go back, reload and try again.</p>",
            status_code=403,
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

    @application.get("/health")
    def health() -> dict[str, str]:
        """Report application liveness without database dependencies."""
        return {"status": "ok", "service": "questly"}

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
    """Build the ASGI app the first time `questly.main:app` is resolved.

    `uvicorn questly.main:app` and `fastapi dev` both need a module attribute,
    but building it at import time would make importing this module — which every
    test does — require a populated `.env`.
    """
    if name == "app":
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
