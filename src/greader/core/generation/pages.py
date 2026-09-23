"""HTML pages T-03 generate (03a/03b/03d) and the T-04 review stepper (04a/04b).

Each stepper step is its own form post with `action` = back | save | next
(step 4: back | save | publish). Every POST handler checks CSRF first.
"""

from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from greader.core.assignments.models import (
    Difficulty,
    JudgingSettings,
    Language,
    TestCase,
    TestCaseKind,
)
from greader.core.auth.csrf import require_csrf
from greader.core.auth.current import current_actor
from greader.core.auth.models import Actor
from greader.core.classrooms.service import ClassroomNotFoundError
from greader.core.generation.models import Draft, DraftPart, DraftSettings
from greader.core.generation.service import (
    ClassroomNotVisibleError,
    DocumentNotAllowedError,
    DraftNotFoundError,
    GenerationFailedError,
    GenerationService,
    MissingFieldsError,
    QuotaExceededError,
)
from greader.core.topics.models import Topic

router = APIRouter(tags=["pages"], include_in_schema=False)

LOCAL_ZONE = ZoneInfo("Asia/Bangkok")
STEP_TEMPLATES = {
    1: "instructor/t04_step1_edit.html",
    2: "instructor/t04_step2_tests.html",
    3: "instructor/t04_step3_settings.html",
    4: "instructor/t04_step4_classrooms.html",
}


def _service(request: Request) -> GenerationService:
    return request.app.state.generation_service


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _see_other(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def _classroom_label(request: Request, actor: Actor, classroom_id: int) -> str:
    try:
        view = request.app.state.classroom_service.view(actor, classroom_id)
    except ClassroomNotFoundError:
        return ""  # the generation use case reports the 404 itself
    return f"{view.classroom.course_name} · Sec {view.classroom.section}"


def _topic_options(request: Request) -> list[tuple[int, str]]:
    topics: list[Topic] = request.app.state.topic_service.list()
    return [(topic.id, topic.name) for topic in topics]


# ---- T-03 -------------------------------------------------------------------


def _generate_page(
    request: Request,
    actor: Actor,
    classroom_id: int,
    *,
    error: str = "",
    form: dict[str, object] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    service = _service(request)
    if form is None:
        form = {
            "prompt": "",
            "difficulty": "medium",
            "topic_id": "",
            "document_ids": [],
        }
    return _templates(request).TemplateResponse(
        request,
        "instructor/t03_generate.html",
        {
            "actor": actor,
            "classroom_id": classroom_id,
            "breadcrumb": _classroom_label(request, actor, classroom_id)
            + " / New problem",
            "documents": service.documents(actor),
            "quota": service.quota(actor),
            "topic_options": _topic_options(request),
            "difficulties": [d.value for d in Difficulty],
            "error": error,
            "form": form,
        },
        status_code=status_code,
    )


@router.get("/classes/{classroom_id}/generate", response_class=HTMLResponse)
def generate_page(
    request: Request, classroom_id: int, draft: int | None = None
) -> HTMLResponse:
    """T-03, or T-03a when `draft` names a Draft just generated."""
    actor = current_actor(request)
    service = _service(request)
    try:
        if draft is None:
            service.drafts(actor, classroom_id)  # visibility: 404 for outsiders
            return _generate_page(request, actor, classroom_id)
        found = service.draft(actor, draft)
    except (ClassroomNotVisibleError, DraftNotFoundError):
        raise HTTPException(status_code=404) from None
    return _templates(request).TemplateResponse(
        request,
        "instructor/t03a_draft.html",
        {
            "actor": actor,
            "classroom_id": classroom_id,
            "breadcrumb": _classroom_label(request, actor, classroom_id)
            + " / New problem",
            "draft": found,
            "sources": _source_names(service, actor),
        },
    )


@router.post("/classes/{classroom_id}/generate", response_model=None)
def generate_submit(
    request: Request,
    classroom_id: int,
    prompt: Annotated[str, Form()],
    difficulty: Annotated[Difficulty, Form()] = Difficulty.MEDIUM,
    topic_id: Annotated[str, Form()] = "",
    document_ids: Annotated[list[int], Form()] = [],  # noqa: B006 -- FastAPI copies it
    csrf_token: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    """T-03 submit; T-03d when the model fails (no quota used)."""
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    form = {
        "prompt": prompt,
        "difficulty": difficulty.value,
        "topic_id": topic_id,
        "document_ids": document_ids,
    }
    try:
        draft = _service(request).generate(
            actor,
            classroom_id,
            prompt=prompt,
            difficulty=difficulty,
            topic_id=int(topic_id) if topic_id else None,
            document_ids=document_ids,
        )
    except ClassroomNotVisibleError:
        raise HTTPException(status_code=404) from None
    except GenerationFailedError:
        return _generate_page(
            request, actor, classroom_id, error="failed", form=form, status_code=502
        )
    except QuotaExceededError:
        return _generate_page(
            request, actor, classroom_id, error="quota", form=form, status_code=429
        )
    except (ValueError, DocumentNotAllowedError):
        return _generate_page(
            request, actor, classroom_id, error="invalid", form=form, status_code=422
        )
    return _see_other(f"/classes/{classroom_id}/generate?draft={draft.id}")


@router.post(
    "/classes/{classroom_id}/drafts/{draft_id}/regenerate", response_model=None
)
def regenerate_submit(
    request: Request,
    classroom_id: int,
    draft_id: int,
    part: Annotated[DraftPart, Form()],
    csrf_token: Annotated[str, Form()] = "",
) -> RedirectResponse:
    require_csrf(request, csrf_token)
    try:
        _service(request).regenerate(current_actor(request), draft_id, part)
    except DraftNotFoundError:
        raise HTTPException(status_code=404) from None
    except (GenerationFailedError, QuotaExceededError):
        pass  # the draft stays as it was; T-03a shows the unchanged part
    return _see_other(f"/classes/{classroom_id}/generate?draft={draft_id}")


# ---- T-04 ---------------------------------------------------------------------


def _step_page(
    request: Request,
    actor: Actor,
    classroom_id: int,
    draft: Draft,
    step: int,
    *,
    missing: list[str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    service = _service(request)
    context = {
        "actor": actor,
        "classroom_id": classroom_id,
        "breadcrumb": _classroom_label(request, actor, classroom_id)
        + " / Review draft",
        "draft": draft,
        "step": step,
        "missing": missing if missing is not None else [],
        "sources": _source_names(service, actor),
    }
    if step == 1:
        context["topic_options"] = _topic_options(request)
        context["difficulties"] = [d.value for d in Difficulty]
    if step == 2:
        context["kinds"] = [k.value for k in TestCaseKind]
    if step == 3:
        context["languages"] = [language.value for language in Language]
        context["deadline_value"] = (
            draft.settings.deadline.astimezone(LOCAL_ZONE).strftime("%Y-%m-%dT%H:%M")
            if draft.settings.deadline is not None
            else ""
        )
    if step == 4:
        context["targets"] = service.publish_targets(actor)
    return _templates(request).TemplateResponse(
        request, STEP_TEMPLATES[step], context, status_code=status_code
    )


def _load(request: Request, actor: Actor, draft_id: int) -> Draft:
    try:
        return _service(request).draft(actor, draft_id)
    except DraftNotFoundError:
        raise HTTPException(status_code=404) from None


@router.get("/classes/{classroom_id}/drafts/{draft_id}", response_class=HTMLResponse)
def stepper_page(
    request: Request, classroom_id: int, draft_id: int, step: int = 1
) -> HTMLResponse:
    """T-04 step 1-4 (`?step=`); T-04b has its own URL, `/published`."""
    actor = current_actor(request)
    if step not in STEP_TEMPLATES:
        raise HTTPException(status_code=404)
    return _step_page(
        request, actor, classroom_id, _load(request, actor, draft_id), step
    )


@router.get(
    "/classes/{classroom_id}/drafts/{draft_id}/published", response_class=HTMLResponse
)
def published_page(request: Request, classroom_id: int, draft_id: int) -> HTMLResponse:
    """T-04b."""
    actor = current_actor(request)
    try:
        draft = _service(request).published(actor, draft_id)
    except DraftNotFoundError:
        raise HTTPException(status_code=404) from None
    return _templates(request).TemplateResponse(
        request,
        "instructor/t04b_published.html",
        {
            "actor": actor,
            "classroom_id": classroom_id,
            "breadcrumb": _classroom_label(request, actor, classroom_id)
            + " / Review draft",
            "draft": draft,
            "targets": _service(request).publish_targets(actor),
        },
    )


def _after_save(
    request: Request,
    actor: Actor,
    classroom_id: int,
    draft_id: int,
    step: int,
    action: str,
) -> HTMLResponse | RedirectResponse:
    """Move per `action`; refuse "next" while the step misses fields (T-04a)."""
    base = f"/classes/{classroom_id}/drafts/{draft_id}"
    if action == "back":
        if step == 1:
            return _see_other(f"/classes/{classroom_id}/generate?draft={draft_id}")
        return _see_other(f"{base}?step={step - 1}")
    if action == "next":
        missing = _service(request).missing_fields(actor, draft_id, step)
        if missing:
            draft = _load(request, actor, draft_id)
            return _step_page(
                request,
                actor,
                classroom_id,
                draft,
                step,
                missing=missing,
                status_code=422,
            )
        return _see_other(f"{base}?step={step + 1}")
    return _see_other(f"{base}?step={step}")


@router.post("/classes/{classroom_id}/drafts/{draft_id}/step1", response_model=None)
def step1_submit(
    request: Request,
    classroom_id: int,
    draft_id: int,
    title: Annotated[str, Form()] = "",
    problem_statement: Annotated[str, Form()] = "",
    difficulty: Annotated[Difficulty, Form()] = Difficulty.MEDIUM,
    topic_id: Annotated[str, Form()] = "",
    action: Annotated[str, Form()] = "save",
    csrf_token: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    _load(request, actor, draft_id)
    _service(request).save(
        actor,
        draft_id,
        title=title,
        problem_statement=problem_statement,
        difficulty=difficulty,
        topic_id=int(topic_id) if topic_id else None,
    )
    return _after_save(request, actor, classroom_id, draft_id, 1, action)


@router.post("/classes/{classroom_id}/drafts/{draft_id}/step2", response_model=None)
def step2_submit(
    request: Request,
    classroom_id: int,
    draft_id: int,
    input_data: Annotated[list[str], Form()] = [],  # noqa: B006
    expected_output: Annotated[list[str], Form()] = [],  # noqa: B006
    kind: Annotated[list[TestCaseKind], Form()] = [],  # noqa: B006
    note: Annotated[list[str], Form()] = [],  # noqa: B006
    delete: Annotated[list[int], Form()] = [],  # noqa: B006
    action: Annotated[str, Form()] = "save",
    csrf_token: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    """Rows arrive as parallel lists; `delete` holds ticked row indexes.

    "+ Add sample/hidden/edge" is `action=add_<kind>`: save, then add an empty
    row of that kind.
    """
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    _load(request, actor, draft_id)
    deleted = set(delete)
    rows = [
        TestCase(input_data=i, expected_output=e, kind=k, note=n.strip())
        for index, (i, e, k, n) in enumerate(
            zip(input_data, expected_output, kind, note, strict=True)
        )
        if index not in deleted
    ]
    _service(request).save(actor, draft_id, test_cases=rows)
    if action.startswith("add_"):
        # An empty row is not stored (save drops blank rows); the page adds one
        # of the requested kind for the Instructor to fill in.
        base = f"/classes/{classroom_id}/drafts/{draft_id}?step=2"
        return _see_other(f"{base}&add={action.removeprefix('add_')}")
    return _after_save(request, actor, classroom_id, draft_id, 2, action)


@router.post("/classes/{classroom_id}/drafts/{draft_id}/step3", response_model=None)
def step3_submit(
    request: Request,
    classroom_id: int,
    draft_id: int,
    deadline: Annotated[str, Form()] = "",
    max_score: Annotated[int, Form()] = 10,
    time_limit_s: Annotated[float, Form()] = 1.0,
    language: Annotated[Language, Form()] = Language.PYTHON3,
    allow_late: Annotated[str, Form()] = "",
    allow_resubmission: Annotated[str, Form()] = "",
    show_hidden_names: Annotated[str, Form()] = "",
    action: Annotated[str, Form()] = "save",
    csrf_token: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    """`deadline` is a datetime-local value in Bangkok time."""
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    _load(request, actor, draft_id)
    parsed = None
    if deadline:
        parsed = datetime.fromisoformat(deadline).replace(tzinfo=LOCAL_ZONE)
    _service(request).save(
        actor,
        draft_id,
        judging=JudgingSettings(
            time_limit_ms=round(time_limit_s * 1000),
            language=language,
            show_hidden_names=show_hidden_names == "on",
        ),
        settings=DraftSettings(
            deadline=parsed,
            max_score=max_score,
            allow_late=allow_late == "on",
            allow_resubmission=allow_resubmission == "on",
        ),
    )
    return _after_save(request, actor, classroom_id, draft_id, 3, action)


@router.post("/classes/{classroom_id}/drafts/{draft_id}/step4", response_model=None)
def step4_submit(
    request: Request,
    classroom_id: int,
    draft_id: int,
    classroom_ids: Annotated[list[int], Form()] = [],  # noqa: B006
    action: Annotated[str, Form()] = "save",
    csrf_token: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    """ "Approve and publish" is `action=publish`."""
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    _load(request, actor, draft_id)
    service = _service(request)
    try:
        service.save(actor, draft_id, classroom_ids=classroom_ids)
    except ClassroomNotVisibleError:
        raise HTTPException(status_code=404) from None
    if action != "publish":
        return _after_save(request, actor, classroom_id, draft_id, 4, action)
    try:
        service.publish(actor, draft_id)
    except MissingFieldsError as error:
        draft = _load(request, actor, draft_id)
        return _step_page(
            request,
            actor,
            classroom_id,
            draft,
            4,
            missing=error.fields,
            status_code=422,
        )
    return _see_other(f"/classes/{classroom_id}/drafts/{draft_id}/published")


def _source_names(service: GenerationService, actor: Actor) -> dict[int, str]:
    """Citation source id → filename, for "lecture-06.pdf · p. 9"."""
    return {document.id: document.filename for document in service.documents(actor)}
