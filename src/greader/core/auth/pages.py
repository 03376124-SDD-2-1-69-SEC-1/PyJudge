"""HTML pages G-01 login, G-03 sign-up, G-04 verify (ADR-0007 route contract)."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from greader.core.auth.current import SESSION_COOKIE, auth_service
from greader.core.auth.models import Landing
from greader.core.auth.routes import set_session_cookie
from greader.core.auth.service import (
    AccountDeactivatedError,
    EmailAlreadyRegisteredError,
    EmailNotVerifiedError,
    FacultyRequiredError,
    InvalidCredentialsError,
    NotKmitlEmailError,
    PasswordMismatchError,
    PasswordTooShortError,
    VerificationLinkExpiredError,
    VerificationLinkInvalidError,
)

router = APIRouter(tags=["pages"], include_in_schema=False)

LANDING_URLS = {
    Landing.CLASSROOMS: "/classes",
    Landing.ADMIN_SETTINGS: "/admin/settings",
}

FACULTIES = (
    "Engineering",
    "Information Technology",
    "Science",
    "Architecture, Art and Design",
    "Industrial Education and Technology",
    "Agricultural Technology",
    "Food Industry",
    "Liberal Arts",
    "Business",
    "Medicine",
    "Dentistry",
    "Other",
)


@dataclass(frozen=True, slots=True)
class DemoAccount:
    """A seeded account listed under "log in as" on G-01 in demo mode only."""

    label: str
    email: str
    password: str


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _demo_accounts(request: Request) -> tuple[DemoAccount, ...]:
    return request.app.state.demo_accounts


def _login_page(
    request: Request, *, email: str = "", error: str = "", status_code: int = 200
) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        request,
        "shared/g01_login.html",
        {"email": email, "error": error, "demo_accounts": _demo_accounts(request)},
        status_code=status_code,
    )


def _signup_page(
    request: Request, *, form: dict[str, str], error: str = "", status_code: int = 200
) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        request,
        "shared/g03_signup.html",
        {"form": form, "error": error, "faculties": FACULTIES},
        status_code=status_code,
    )


def _verify_page(
    request: Request, *, state: str, email: str = "", status_code: int = 200
) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        request,
        "shared/g04_verify.html",
        {"state": state, "email": email},
        status_code=status_code,
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    """G-01."""
    return _login_page(request)


@router.post("/login", response_model=None)
def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    """G-01 submit: 01a wrong password, 01b email not verified."""
    try:
        result = auth_service(request).log_in(email=email, password=password)
    except InvalidCredentialsError:
        return _login_page(
            request, email=email, error="wrong_password", status_code=401
        )
    except EmailNotVerifiedError:
        return _login_page(request, email=email, error="not_verified", status_code=403)
    except AccountDeactivatedError:
        return _login_page(request, email=email, error="deactivated", status_code=403)
    response = RedirectResponse(
        LANDING_URLS[result.landing], status_code=status.HTTP_303_SEE_OTHER
    )
    set_session_cookie(response, result.token)
    return response


@router.post("/logout")
def logout_submit(request: Request) -> RedirectResponse:
    token = request.cookies.get(SESSION_COOKIE)
    if token is not None:
        auth_service(request).log_out(token)
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request) -> HTMLResponse:
    """G-03."""
    return _signup_page(request, form={})


@router.post("/signup", response_class=HTMLResponse)
def signup_submit(
    request: Request,
    full_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
    wants_instructor: Annotated[str, Form()] = "",
    faculty: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """G-03 submit: 03a not a KMITL email, 03b already registered; success → G-04a."""
    form = {
        "full_name": full_name,
        "email": email,
        "wants_instructor": wants_instructor,
        "faculty": faculty,
    }
    error = ""
    try:
        user = auth_service(request).sign_up(
            full_name=full_name,
            email=email,
            password=password,
            confirm_password=confirm_password,
            wants_instructor=wants_instructor == "on",
            faculty=faculty,
        )
    except NotKmitlEmailError:
        error = "not_kmitl_email"
    except EmailAlreadyRegisteredError:
        error = "already_registered"
    except PasswordTooShortError:
        error = "password_too_short"
    except PasswordMismatchError:
        error = "password_mismatch"
    except FacultyRequiredError:
        error = "faculty_required"
    except ValueError:
        error = "full_name_required"
    if error:
        return _signup_page(request, form=form, error=error, status_code=422)
    return _verify_page(request, state="waiting", email=user.email)


@router.get("/verify", response_class=HTMLResponse)
def verify_page(request: Request, token: str = "") -> HTMLResponse:
    """G-04: 04a waiting (no token), 04b verified, 04c link expired."""
    if not token:
        return _verify_page(request, state="waiting")
    try:
        user = auth_service(request).verify_email(token)
    except VerificationLinkExpiredError:
        return _verify_page(request, state="expired", status_code=410)
    except VerificationLinkInvalidError:
        return _verify_page(request, state="invalid", status_code=400)
    return _verify_page(request, state="verified", email=user.email)


@router.post("/verify/resend", response_class=HTMLResponse)
def verify_resend(request: Request, email: Annotated[str, Form()]) -> HTMLResponse:
    """G-01b / G-04c "Send a new link"."""
    auth_service(request).resend_verification(email)
    return _verify_page(request, state="waiting", email=email)
