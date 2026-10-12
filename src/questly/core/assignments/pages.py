"""HTML pages T-05 edit a published problem (05a extend the deadline) and the
T-02 "Notify students" post.

T-05 is one form: the content, the reason for the change and, in the 05a
dialog, which Postings get a new deadline. One POST carries all of it to
`AssignmentService.edit`. Every POST handler checks CSRF first.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from questly.core.assignments.models import (
    Assignment,
    Difficulty,
    InstructorProblem,
    JudgingSettings,
    Language,
    Posting,
    TestCase,
    TestCaseKind,
)
from questly.core.assignments.service import (
    AssignmentNotFoundError,
    AssignmentService,
    ClassroomNotVisibleError,
    PostingNotFoundError,
)
from questly.core.auth.csrf import require_csrf
from questly.core.auth.current import current_actor
from questly.core.auth.models import Actor, PermissionDeniedError
from questly.core.topics.models import Topic

router = APIRouter(tags=["pages"], include_in_schema=False)

LOCAL_ZONE = ZoneInfo("Asia/Bangkok")
INPUT_FORMAT = "%Y-%m-%dT%H:%M"
SUGGESTED_EXTENSION = timedelta(days=7)
# What a page answers with 404: the Assignment or Posting is not there for the Actor.
NOT_VISIBLE = (AssignmentNotFoundError, ClassroomNotVisibleError, PostingNotFoundError)
KINDS = (
    (TestCaseKind.SAMPLE, "Sample tests", "shown to students", "+ Add sample"),
    (TestCaseKind.HIDDEN, "Hidden tests", "pass/fail only", "+ Add hidden"),
    (TestCaseKind.EDGE, "Edge cases", "", "+ Add edge case"),
)


@dataclass(slots=True)
class RowForm:
    """One Test Case row of the form; `id` is empty for a row not saved yet."""

    kind: str
    input_data: str = ""
    expected_output: str = ""
    note: str = ""
    id: str = ""


@dataclass(slots=True)
class PostingChoice:
    """One line of the 05a dialog: a Posting and whether it gets a new deadline."""

    posting_id: int
    classroom_label: str
    deadline: datetime
    submitted: int
    members: int
    extend: bool
    extend_to: str


@dataclass(slots=True)
class EditForm:
    title: str
    problem_statement: str
    difficulty: str
    topic_id: str
    reason: str = ""
    rows: list[RowForm] = field(default_factory=list)
    time_limit_s: str = "1.0"
    language: str = Language.PYTHON3.value
    show_hidden_names: bool = False
    choices: list[PostingChoice] = field(default_factory=list)


def _service(request: Request) -> AssignmentService:
    return request.app.state.assignment_service


def _see_other(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def _t02(classroom_id: int, assignment_id: int) -> str:
    return f"/classes/{classroom_id}/assignments/{assignment_id}"


def _local_input(value: datetime) -> str:
    return value.astimezone(LOCAL_ZONE).strftime(INPUT_FORMAT)


def _to_utc(value: str) -> datetime:
    """A `datetime-local` value is Bangkok time; the service stores UTC."""
    return datetime.fromisoformat(value).replace(tzinfo=LOCAL_ZONE).astimezone(UTC)


def _owner_problem(
    request: Request, actor: Actor, classroom_id: int, assignment_id: int
) -> InstructorProblem:
    """The Posting of this URL for its owning Instructor.

    A Member of the Classroom gets a StudentProblem back, which is a 403; an
    outsider or a missing Posting is a 404.
    """
    try:
        problem = _service(request).problem(actor, classroom_id, assignment_id)
    except NOT_VISIBLE:
        raise HTTPException(status_code=404) from None
    if not isinstance(problem, InstructorProblem):
        raise PermissionDeniedError
    return problem


def _classroom_label(request: Request, actor: Actor, classroom_id: int) -> str:
    view = request.app.state.classroom_service.view(actor, classroom_id)
    return f"{view.classroom.course_name} · Sec {view.classroom.section}"


def _submitted(request: Request, actor: Actor, posting: Posting) -> int:
    problem = _owner_problem(
        request, actor, posting.classroom_id, posting.assignment_id
    )
    return problem.summary.submitted


def _choices(
    request: Request,
    actor: Actor,
    assignment_id: int,
    classroom_id: int,
    postings: list[Posting],
) -> list[PostingChoice]:
    """05a lists every Posting; the Classroom being edited from is pre-checked."""
    return [
        PostingChoice(
            posting_id=posting.id,
            classroom_label=_classroom_label(request, actor, posting.classroom_id),
            deadline=posting.schedule.deadline,
            submitted=_submitted(request, actor, posting),
            members=len(
                request.app.state.classroom_service.member_ids(
                    actor, posting.classroom_id
                )
            ),
            extend=posting.classroom_id == classroom_id,
            extend_to=_local_input(posting.schedule.deadline + SUGGESTED_EXTENSION),
        )
        for posting in sorted(postings, key=lambda item: item.classroom_id)
    ]


def _initial_form(assignment: Assignment, choices: list[PostingChoice]) -> EditForm:
    return EditForm(
        title=assignment.title,
        problem_statement=assignment.problem_statement,
        difficulty=assignment.difficulty.value,
        topic_id=str(assignment.topic_id) if assignment.topic_id is not None else "",
        rows=[
            RowForm(
                kind=test_case.kind.value,
                input_data=test_case.input_data,
                expected_output=test_case.expected_output,
                note=test_case.note,
                id=str(test_case.id) if test_case.id is not None else "",
            )
            for test_case in assignment.test_cases
        ],
        time_limit_s=f"{assignment.settings.time_limit_ms / 1000:.1f}",
        language=assignment.settings.language.value,
        show_hidden_names=assignment.settings.show_hidden_names,
        choices=choices,
    )


def _edit_page(
    request: Request,
    actor: Actor,
    problem: InstructorProblem,
    form: EditForm,
    *,
    error: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    classroom_id = problem.posting.classroom_id
    topics: list[Topic] = request.app.state.topic_service.list()
    return request.app.state.templates.TemplateResponse(
        request,
        "instructor/t05_edit.html",
        {
            "actor": actor,
            "classroom_id": classroom_id,
            "assignment": problem.assignment,
            "number": problem.number,
            "breadcrumb": f"{_classroom_label(request, actor, classroom_id)}"
            f" / Problem {problem.number} / Edit",
            "t02_url": _t02(classroom_id, problem.assignment.id),
            "form": form,
            "error": error,
            "kinds": KINDS,
            "difficulties": [d.value for d in Difficulty],
            "topic_options": [(topic.id, topic.name) for topic in topics],
            "submitted_total": sum(choice.submitted for choice in form.choices),
            "member_total": sum(choice.members for choice in form.choices),
            "next_version": problem.assignment.current_version + 1,
        },
        status_code=status_code,
    )


@router.get(
    "/classes/{classroom_id}/assignments/{assignment_id}/edit",
    response_class=HTMLResponse,
)
def edit_page(request: Request, classroom_id: int, assignment_id: int) -> HTMLResponse:
    """T-05."""
    actor = current_actor(request)
    problem = _owner_problem(request, actor, classroom_id, assignment_id)
    postings = _service(request).postings_of(actor, assignment_id)
    choices = _choices(request, actor, assignment_id, classroom_id, postings)
    return _edit_page(
        request, actor, problem, _initial_form(problem.assignment, choices)
    )


def _rows(
    kind: list[str],
    input_data: list[str],
    expected_output: list[str],
    note: list[str],
    test_case_id: list[str],
    delete: list[int],
) -> list[RowForm]:
    """Rows arrive as parallel lists; `delete` holds ticked row indexes."""
    deleted = set(delete)
    return [
        RowForm(kind=k, input_data=i, expected_output=e, note=n, id=t)
        for index, (k, i, e, n, t) in enumerate(
            zip(kind, input_data, expected_output, note, test_case_id, strict=True)
        )
        if index not in deleted
    ]


def _test_cases(rows: list[RowForm]) -> list[TestCase]:
    """A new row left empty is dropped; a saved row keeps its id."""
    return [
        TestCase(
            input_data=row.input_data,
            expected_output=row.expected_output,
            kind=TestCaseKind(row.kind),
            note=row.note.strip(),
            id=int(row.id) if row.id else None,
        )
        for row in rows
        if row.id
        or row.input_data.strip()
        or row.expected_output.strip()
        or row.note.strip()
    ]


def _posted_choices(
    choices: list[PostingChoice],
    posting_id: list[int],
    extend_to: list[str],
    extend: list[int],
) -> list[PostingChoice]:
    """The dialog as posted: Postings from the server, the choices from the form."""
    posted = dict(zip(posting_id, extend_to, strict=True))
    for choice in choices:
        choice.extend = choice.posting_id in extend
        choice.extend_to = posted.get(choice.posting_id, choice.extend_to)
    return choices


@router.post(
    "/classes/{classroom_id}/assignments/{assignment_id}/edit", response_model=None
)
def edit_submit(
    request: Request,
    classroom_id: int,
    assignment_id: int,
    title: Annotated[str, Form()] = "",
    problem_statement: Annotated[str, Form()] = "",
    difficulty: Annotated[Difficulty, Form()] = Difficulty.MEDIUM,
    topic_id: Annotated[str, Form()] = "",
    reason: Annotated[str, Form()] = "",
    kind: Annotated[list[str], Form()] = [],  # noqa: B006 -- FastAPI copies it
    input_data: Annotated[list[str], Form()] = [],  # noqa: B006
    expected_output: Annotated[list[str], Form()] = [],  # noqa: B006
    note: Annotated[list[str], Form()] = [],  # noqa: B006
    test_case_id: Annotated[list[str], Form()] = [],  # noqa: B006
    delete: Annotated[list[int], Form()] = [],  # noqa: B006
    time_limit_s: Annotated[float, Form()] = 1.0,
    language: Annotated[Language, Form()] = Language.PYTHON3,
    show_hidden_names: Annotated[str, Form()] = "",
    posting_id: Annotated[list[int], Form()] = [],  # noqa: B006
    extend_to: Annotated[list[str], Form()] = [],  # noqa: B006
    extend: Annotated[list[int], Form()] = [],  # noqa: B006
    action: Annotated[str, Form()] = "save",
    csrf_token: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    """Save as a new Version; `action=add_<kind>` only adds an empty row."""
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    service = _service(request)
    problem = _owner_problem(request, actor, classroom_id, assignment_id)
    choices = _choices(
        request,
        actor,
        assignment_id,
        classroom_id,
        service.postings_of(actor, assignment_id),
    )
    form = EditForm(
        title=title,
        problem_statement=problem_statement,
        difficulty=difficulty.value,
        topic_id=topic_id,
        reason=reason,
        rows=_rows(kind, input_data, expected_output, note, test_case_id, delete),
        time_limit_s=str(time_limit_s),
        language=language.value,
        show_hidden_names=show_hidden_names == "on",
        choices=_posted_choices(choices, posting_id, extend_to, extend),
    )
    if action.startswith("add_"):
        form.rows.append(RowForm(kind=action.removeprefix("add_")))
        return _edit_page(request, actor, problem, form)
    try:
        service.edit(
            actor,
            assignment_id,
            reason=reason,
            title=title,
            problem_statement=problem_statement,
            difficulty=difficulty,
            topic_id=int(topic_id) if topic_id else None,
            test_cases=_test_cases(form.rows),
            settings=JudgingSettings(
                time_limit_ms=round(time_limit_s * 1000),
                language=language,
                show_hidden_names=form.show_hidden_names,
            ),
            extend_deadlines=_extensions(form.choices),
        )
    except ValueError as refusal:
        return _edit_page(
            request,
            actor,
            problem,
            form,
            error=_sentence(str(refusal)),
            status_code=422,
        )
    except NOT_VISIBLE:
        raise HTTPException(status_code=404) from None
    return _see_other(_t02(classroom_id, assignment_id))


def _extensions(choices: list[PostingChoice]) -> dict[int, datetime]:
    """Posting id → new deadline for each ticked line of 05a."""
    ticked = [choice for choice in choices if choice.extend]
    if any(not choice.extend_to for choice in ticked):
        raise ValueError("choose a new deadline for every classroom you extend")
    return {choice.posting_id: _to_utc(choice.extend_to) for choice in ticked}


def _sentence(message: str) -> str:
    return message[:1].upper() + message[1:] + "."


@router.post(
    "/classes/{classroom_id}/assignments/{assignment_id}/notify", response_model=None
)
def notify_students(
    request: Request,
    classroom_id: int,
    assignment_id: int,
    csrf_token: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """T-02c "Notify students"; T-02 confirms with `?notified=1`."""
    require_csrf(request, csrf_token)
    try:
        _service(request).notify_students(
            current_actor(request), classroom_id, assignment_id
        )
    except NOT_VISIBLE:
        raise HTTPException(status_code=404) from None
    return _see_other(f"{_t02(classroom_id, assignment_id)}?notified=1")
