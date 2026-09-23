"""HTML pages C-01 picker, C-02 join, C-03 create, and /classes/{id} (T-01, S-01).

Tabs are URLs (`?tab=`); modals are `popover` elements; every action is a
form post followed by a redirect.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from greader.core.assignments.models import ProblemFilter
from greader.core.assignments.service import AssignmentService
from greader.core.auth.csrf import require_csrf
from greader.core.auth.current import current_actor
from greader.core.auth.models import Actor, PermissionDeniedError
from greader.core.classrooms.models import (
    ClassroomFilter,
    InstructorClassroomView,
    InstructorPicker,
)
from greader.core.classrooms.service import (
    ClassroomNotFoundError,
    ClassroomService,
    InvalidJoinCodeError,
    MemberNotFoundError,
)

router = APIRouter(tags=["pages"], include_in_schema=False)

INSTRUCTOR_TABS = {
    "problems": "instructor/t01_problems.html",
    "summary": "instructor/t01_summary.html",
    "members": "instructor/t01_members.html",
    "settings": "instructor/t01_settings.html",
}
STUDENT_TABS = {
    "problems": "student/s01_problems.html",
    "summary": "student/s01_summary.html",
}


def _service(request: Request) -> ClassroomService:
    return request.app.state.classroom_service


def _assignments(request: Request) -> AssignmentService:
    """T-01/S-01 Problems and Summary tabs are drawn from the assignments slice."""
    return request.app.state.assignment_service


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _see_other(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def _picker_page(
    request: Request,
    actor: Actor,
    *,
    classroom_filter: ClassroomFilter,
    created_id: int | None = None,
    join_error: bool = False,
    join_code: str = "",
) -> HTMLResponse:
    service = _service(request)
    picker = service.picker(actor, classroom_filter)
    context = {"actor": actor, "picker": picker, "filter": classroom_filter.value}
    if isinstance(picker, InstructorPicker):
        created = None
        if created_id is not None:
            created = service.view(actor, created_id).classroom
        context["created"] = created
        return _templates(request).TemplateResponse(
            request, "shared/c01_instructor.html", context
        )
    context["join_error"] = join_error
    context["join_code"] = join_code
    return _templates(request).TemplateResponse(
        request,
        "shared/c01_student.html",
        context,
        status_code=422 if join_error else 200,
    )


@router.get("/classes", response_class=HTMLResponse)
def classes_page(
    request: Request,
    filter: ClassroomFilter = ClassroomFilter.ALL,
    created: int | None = None,
) -> HTMLResponse:
    """C-01 (01a/01b empty); `created` shows C-03a with the new Join code."""
    return _picker_page(
        request, current_actor(request), classroom_filter=filter, created_id=created
    )


@router.post("/classes")
def create_submit(
    request: Request,
    course_code: Annotated[str, Form()],
    course_name: Annotated[str, Form()],
    section: Annotated[str, Form()],
    semester: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """C-03 submit."""
    require_csrf(request, csrf_token)
    classroom = _service(request).create(
        current_actor(request),
        course_code=course_code,
        course_name=course_name,
        section=section,
        semester=semester,
    )
    return _see_other(f"/classes?created={classroom.id}")


@router.post("/classes/join", response_model=None)
def join_submit(
    request: Request,
    join_code: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()] = "",
) -> RedirectResponse | HTMLResponse:
    """C-02 submit; C-02a on an invalid code."""
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    try:
        classroom = _service(request).join(actor, join_code)
    except InvalidJoinCodeError:
        return _picker_page(
            request,
            actor,
            classroom_filter=ClassroomFilter.ALL,
            join_error=True,
            join_code=join_code,
        )
    return _see_other(f"/classes/{classroom.id}")


@router.get("/classes/{classroom_id}", response_class=HTMLResponse)
def classroom_page(
    request: Request,
    classroom_id: int,
    tab: str = "problems",
    filter: ProblemFilter = ProblemFilter.ALL,
) -> HTMLResponse:
    """T-01 for the owner, S-01 for a Member; 404 for anyone else."""
    actor = current_actor(request)
    service = _service(request)
    try:
        view = service.view(actor, classroom_id)
    except ClassroomNotFoundError:
        raise HTTPException(status_code=404) from None
    tabs = (
        INSTRUCTOR_TABS if isinstance(view, InstructorClassroomView) else STUDENT_TABS
    )
    if tab not in INSTRUCTOR_TABS and tab not in STUDENT_TABS:
        raise HTTPException(status_code=404)
    if tab not in tabs:
        # A Member asking for an Instructor tab (ADR-0007 §9.6).
        raise PermissionDeniedError
    context = {
        "actor": actor,
        "view": view,
        "tab": tab,
        "breadcrumb": f"{view.classroom.course_code} {view.classroom.course_name} "
        f"· Sec {view.classroom.section}",
    }
    if tab == "members":
        context["members"] = service.members(actor, classroom_id)
    if tab == "problems":
        context["problems"] = _assignments(request).problems(
            actor, classroom_id, filter
        )
        context["filter"] = filter.value
        if isinstance(view, InstructorClassroomView):
            generation = request.app.state.generation_service
            context["drafts"] = generation.drafts(actor, classroom_id)
            context["draft_sources"] = {
                document.id: document.filename
                for document in generation.documents(actor)
            }
    if tab == "summary":
        context["summary"] = _assignments(request).summary(actor, classroom_id)
    return _templates(request).TemplateResponse(request, tabs[tab], context)


@router.post("/classes/{classroom_id}/settings")
def settings_submit(
    request: Request,
    classroom_id: int,
    course_code: Annotated[str, Form()],
    course_name: Annotated[str, Form()],
    section: Annotated[str, Form()],
    semester: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()] = "",
) -> RedirectResponse:
    require_csrf(request, csrf_token)
    _owner_action(
        lambda service, actor: service.update(
            actor,
            classroom_id,
            course_code=course_code,
            course_name=course_name,
            section=section,
            semester=semester,
        ),
        request,
    )
    return _see_other(f"/classes/{classroom_id}?tab=settings")


@router.post("/classes/{classroom_id}/archive")
def archive_submit(
    request: Request, classroom_id: int, csrf_token: Annotated[str, Form()] = ""
) -> RedirectResponse:
    require_csrf(request, csrf_token)
    _owner_action(lambda service, actor: service.archive(actor, classroom_id), request)
    return _see_other(f"/classes/{classroom_id}?tab=settings")


@router.post("/classes/{classroom_id}/unarchive")
def unarchive_submit(
    request: Request, classroom_id: int, csrf_token: Annotated[str, Form()] = ""
) -> RedirectResponse:
    require_csrf(request, csrf_token)
    _owner_action(
        lambda service, actor: service.unarchive(actor, classroom_id), request
    )
    return _see_other(f"/classes/{classroom_id}?tab=settings")


@router.post("/classes/{classroom_id}/join-code/regenerate")
def regenerate_submit(
    request: Request, classroom_id: int, csrf_token: Annotated[str, Form()] = ""
) -> RedirectResponse:
    require_csrf(request, csrf_token)
    _owner_action(
        lambda service, actor: service.regenerate_join_code(actor, classroom_id),
        request,
    )
    return _see_other(f"/classes/{classroom_id}?tab=settings")


@router.post("/classes/{classroom_id}/join-code/disable")
def disable_submit(
    request: Request, classroom_id: int, csrf_token: Annotated[str, Form()] = ""
) -> RedirectResponse:
    require_csrf(request, csrf_token)
    _owner_action(
        lambda service, actor: service.disable_join_code(actor, classroom_id), request
    )
    return _see_other(f"/classes/{classroom_id}?tab=settings")


@router.post("/classes/{classroom_id}/members/{user_id}/remove")
def remove_member_submit(
    request: Request,
    classroom_id: int,
    user_id: int,
    csrf_token: Annotated[str, Form()] = "",
) -> RedirectResponse:
    require_csrf(request, csrf_token)
    try:
        _owner_action(
            lambda service, actor: service.remove_member(actor, classroom_id, user_id),
            request,
        )
    except MemberNotFoundError:
        raise HTTPException(status_code=404) from None
    return _see_other(f"/classes/{classroom_id}?tab=members")


def _owner_action(
    action: Callable[[ClassroomService, Actor], object], request: Request
) -> None:
    """Run an Instructor-only use case, mapping an invisible Classroom to 404."""
    try:
        action(_service(request), current_actor(request))
    except ClassroomNotFoundError:
        raise HTTPException(status_code=404) from None
