# AGENTS.md — GReader

Modular monolith: one FastAPI + Jinja2 app in one repo, one Neon project.
`core/` and `ai/` are modules of that app, not separate services; they call
each other through Python interfaces (`typing.Protocol`), never over HTTP.
A classroom system for programming courses: Instructors publish Assignments
(drafted by the AI slice from their lecture notes) to Classrooms, and Students
submit code that is judged.
The flow and every decision behind it: `docs/adr/0007-classroom-centric-flow.md`.
Domain words: `CONTEXT.md`.

**UI source of truth:** the Figma file GradeFlow (fileKey
`WecQlqyFS71jLCNmD6U1jE`) for the pages พาย has mocked. A page without a mock
follows `docs/wireframes/GReader wireframes - Prototype.html` until it has one.
Do not call the Figma MCP in a task unless the task says so (the Starter plan
quota is used up). UI-01 in `docs/task-scope.md` tracks which template matches
which Figma frame.

This file holds the rules an agent needs to not break things. Human-facing
setup and background live in `README.md` and `docs/adr/`.

## Status

| Area                          | State                                                                                              | Owner (task)        |
| ----------------------------- | -------------------------------------------------------------------------------------------------- | ------------------- |
| `core/topics`                 | Working. **The reference slice — copy its shape.**                                                 | shared              |
| `core/auth`, `classrooms`     | Working on fakes (demo mode); **503 in production until OPS-15**                                   | done (CORE-12, 13)  |
| `core/assignments`            | Versions and Postings on fakes; **503 in production until OPS-15**                                 | done (CORE-14)      |
| `core/generation`             | Drafts, T-03/T-04, daily Quota on fakes; **503 until OPS-15**; production client is a stub         | done (CORE-15)      |
| `core/submissions`            | Run vs Submit, PostingStats on fakes; **503 until OPS-15**; production `CodeRunner` is a stub      | พาย (CORE-17)       |
| `core/uploads`                | Working; to be renamed `core/documents`                                                            | open (CORE-16)      |
| `core/notifications`, `admin` | Not started                                                                                        | open (CORE-18, 19)  |
| `database/`                   | 9 tables live on Neon; classroom, posting, version, submission, notification and auth tables wait for OPS-15 | พาย (OPS-15)        |
| `ai/`                         | Vector storage works (AI-01). Ingestion, retrieval and a real `GenerationClient` are not started; the standalone app in `ai/app/main.py` is unused | ฟิล์ม (AI-02 to 07), พาย (OPS-16) |
| `web/templates/`              | Every page of ADR-0007 except T-05, T-06 and A-01 exists; matching them to Figma is UI-01          | พาย (UI-01)         |

"Working on fakes" means the slice runs in demo mode (`scripts/demo.py`) and in
tests. In production it is wired to `database/pending.py`, which refuses every
call, so its routes answer 503 until OPS-15 lands the tables and SQL adapters.
Every SQL adapter is OPS-15's work; a slice's task never lists one.

Do not implement another area's placeholder unless the task says to.

## Stack

Python 3.12+ · FastAPI · Jinja2 · uv · Pytest · Ruff · Tailwind (standalone CLI)

```
SQLModel        <- models written here (wraps SQLAlchemy 2.x + Pydantic)
SQLAlchemy 2.x  <- the actual ORM
psycopg v3      <- driver
PostgreSQL      <- Neon, schemas `core` and `rag`, pgvector extension
```

- **Everything is synchronous.** No `async def`, no `AsyncSession`, no async
  drivers, anywhere.
- Domain services are pulled off `request.app.state`, never injected with
  `Depends()`. The only exceptions are the infrastructure health checks in
  `main.py` — do not copy that pattern into a slice.
- DSN must be `postgresql+psycopg://`. Anything else resolves to psycopg2,
  which is not installed, and fails with an unhelpful `NoSuchModuleError`.
- SQLModel does not re-export everything; `from sqlalchemy import Column,
BigInteger` is expected and correct.
- pgvector is not an ORM — it is an extension plus a `Vector` column type.

## Layering

```
routes.py → service.py → ports.py (Protocol) → adapter
```

| File            | Holds                                     | Must not import              |
| --------------- | ----------------------------------------- | ---------------------------- |
| `models.py`     | domain model (frozen slotted dataclass)   | FastAPI, ORM, storage client |
| `schemas.py`    | request/response shapes for OpenAPI       | business rules               |
| `ports.py`      | `typing.Protocol`                         | HTTP                         |
| `service.py`    | use cases; takes the repo via constructor | FastAPI, ORM, SQL            |
| `routes.py`     | JSON API under `/api/v1/`: HTTP in, service call, error mapping | business rules, SQL, templates |
| `pages.py`      | HTML pages: HTTP in, service call, pick a template | business rules, SQL, `/api` prefix |

The in-memory adapter is not part of the slice — it lives in
`tests/fakes/<slice>.py` (e.g. `tests/fakes/topics.py`), satisfying the same
Protocol as the SQL adapter under `database/`.

Database adapters live only in `database/core/<slice>_repository.py`.
Nothing under `core/` may import an ORM or a storage client.
`ai` may import `core` domain models; `core` must never import `ai`.

`main.py` is the composition root: build repos and services, put them on
`app.state`, include routers, mount static files. No business rules there.

**When adding a slice, read `core/topics/` first and follow it.** It is the
one executable reference; prose in this file does not override it.

## Schema rules (locked — do not "fix" these)

- Primary keys are `BIGSERIAL` (int), not UUID. (In-memory Topics still uses
  UUID; that is the demo, not the pattern to copy for persisted tables.)
- One Neon project, two schemas: `core` and `rag`.
- **No foreign keys across schemas.** `core` and `rag` share one database and
  one app; the modules reach each other through Python interfaces, and cleanup
  across the two schemas is done by the application, not by a cascade.
- `assignments.artifact_id` is nullable and UNIQUE.
- `test_cases` has no `title` column. Do not add one. The per-test label is
  `note`, and `kind` (sample, hidden, edge) replaces `is_hidden` — both
  arrive with the ADR-0007 schema task, not before.
- Tables for classrooms, postings, versions, submissions, notifications and
  auth are proposed in ADR-0007 "Schema changes". Until that OPS task merges
  they do not exist; do not write SQL adapters for them.
- Embeddings are `VECTOR(768)`.
- Some columns look redundant on purpose — `knowledge_sources.r2_object_key`,
  `knowledge_sources.metadata`, `knowledge_chunks.embedding_model`,
  `generation_artifacts.citations.text_snapshot`. They exist because there is
  no cross-schema FK. Do not remove them.

## Do not do these without a task saying so

- Do not run `alembic upgrade`, `downgrade`, or `--autogenerate` against the
  shared database. It is shared across the team; a downgrade destroys other
  people's work. The one exception is CI, which runs `alembic upgrade head`
  against a Neon branch it creates and deletes within the same run.
- Do not create or edit migration files.
- Do not edit `.env`, `.env.example`, or anything holding credentials.
- Do not add `<script>`, `javascript:` URLs, or inline handlers (`onclick`,
  `onload`, …) to templates. An architecture test enforces this.
- Do not hand-edit `static/css/app.css` — edit `input.css` and rebuild.
- Do not add new files outside the agreed scope. `.gitignore` does not
  technically block this — it only ignores build/venv/cache noise — so this
  is a team rule to follow, not a tooling gate.

If a task looks like it needs a schema change, stop and say so.

## Who may change database and locked files

All of `src/greader/database/` and `alembic/` belong to พาย (GitHub
`Doonminus2`), in every case. A task whose description seems to need a
`database/` or `alembic/` edit is not an exception — stop and ask พาย instead
of editing it. `docs/task-scope.md` enforces this at the row level: it never
grants a `database/` or `alembic/` path to a row owned by anyone else.

A subset of that — the paths under "Off-limits regardless of task" in
`docs/task-scope.md` (`alembic/`, credentials, `database/core/tables.py`,
`database/rag/tables.py`, `pyproject.toml` dependencies, CI config, `AGENTS.md`
itself) — is locked further still: those change only through an OPS task, and
anyone else who needs one changed asks; they do not edit it and explain
afterwards.

`.github/CODEOWNERS` is what enforces that stricter subset: a pull request
touching one of those paths cannot merge without a review from the owner. That
file is the mechanism, `docs/task-scope.md`'s off-limits list is the reason —
if the two ever disagree, CODEOWNERS wins and the list is what's out of date.

## Known trap: alembic autogenerate

Autogenerate only sees models imported into `SQLModel.metadata`. A missing
import produces a migration with missing tables **silently, with no error**,
and the next run may emit `drop_table` for tables that exist.
`database/__init__.py` must import both `core.tables` and `rag.tables`.

`CREATE SCHEMA`, `CREATE EXTENSION vector`, and the HNSW index cannot be
autogenerated. All three are already written by hand in the history.

## Task scope

Before touching code, read `docs/task-scope.md`. Find the row matching the
current branch's TASK-ID (`<type>/<TASK-ID>-<slug>`) and stay inside its "May
touch" column. This applies to every agent, not just Claude Code — `/grill-me`
(Claude Code only) reads the same file automatically; agents without
slash-command support must open `docs/task-scope.md` themselves at the start
of a session.

The row's Status is `open`, `in-progress` or `done`, and it is the only thing
that says whether a task is available. `/start-task` offers `open` rows owned by
you or by `TBD`, and your `in-progress` rows; it hides a row whose paths no
longer exist. A path the task must create is written `creates:` in its row.
`uv run python -m scripts.task_scope <owner>` prints the same list.

## Terminology

Instructor (not teacher/user) · Student (not learner) · Classroom (not
class/course/room) · Member · Join code · Assignment (not challenge/task/question)
· Posting · Version · Draft · Submission (not attempt) · Run · Late · Test Case
(not example/check) · Topic (not tag/category/label).

Code and API say Assignment; UI copy says "Problem" / "โจทย์". Definitions and
the full list: `CONTEXT.md`.

## Ports and adapters

Every external dependency — AI service, database, storage — is called through
a `typing.Protocol` defined in the module that needs it, never through a
concrete client type directly.

- The Protocol is the port. It lives next to the code that uses it
  (e.g. `core/generation/ports.py` defines the Protocol and its interface;
  `ai/client.py` provides an adapter that implements it).
- Ports named by ADR-0007: `GenerationClient` (generation), `CodeRunner`
  (submissions; Judge0 CE), `EmailSender` (notifications — auth sends mail
  through `NotificationService`, not its own Protocol), `AssignmentPublisher`
  (generation, filled with `AssignmentService`).
- Concrete adapters for outside services live in `src/greader/integrations/`
  (Judge0, email); database and storage adapters stay in `database/`.
  `core/` never imports `greader.integrations`.
- Concrete implementations are adapters: a stub for tests/mocks, a real one
  for production. Both satisfy the same Protocol.
- Callers (services, routes) type-hint against the Protocol only. They must
  never import a concrete adapter class directly — only `main.py` picks the
  adapter and puts it on `app.state`.
- Swapping an adapter (mock → real, in-memory → database) must never require
  changing the Protocol, the caller, or the route.

If a task looks like it needs the caller to know which adapter it's talking
to, stop — that means the Protocol is missing a method, not that the caller
should reach past it.

## Commands

```bash
uv sync
uv run fastapi dev src/greader/main.py

uv run pytest
uv run ruff check .
uv run ruff format --check .   # `ruff format .` to fix

uv run python -m scripts.demo  # demo mode, http://127.0.0.1:8000/login
ALLOW_UNSAFE_RUNNER=1 uv run python -m scripts.demo  # also execute Run/Submit code, unsandboxed

# app.css from input.css — Tailwind v4.3.3 standalone binary, see README "Styles"
tailwindcss -i src/greader/web/static/css/input.css -o src/greader/web/static/css/app.css
tailwindcss -i src/greader/web/static/css/input.css -o src/greader/web/static/css/app.css --watch
```

**Demo mode** (`scripts/demo.py`) runs the app on the in-memory fakes from
`tests/fakes/` with a seed mirroring `docs/wireframes/`, so pages are clickable
before OPS-15 creates the tables. G-01 lists every seeded account under "log in
as"; verification links are logged, not emailed; data is lost on restart. It
lives outside `src/` because fakes may not ship in the package. When a slice
lands, extend `DemoSeed` so its pages have data. `fastapi dev` still wires the
real adapters, and every classroom slice answers 503 there until OPS-15.

`tests/unit/` domain + service · `tests/integration/` HTTP via ASGI transport ·
`tests/architecture/` import direction and the no-JavaScript rule ·
`tests/db/` database adapters against a real PostgreSQL · `tests/r2/` object
storage behaviour against a real R2 bucket.

Tests must never hit the shared database, the real R2 bucket, or a real AI
provider. `tests/db/` and `tests/r2/` are the exceptions, and only through
throwaway infrastructure:

- `tests/db/` — mark tests `postgres`, read the DSN from the `postgres_url`
  fixture, and never from `DATABASE_URL`. CI supplies `POSTGRES_TEST_URL` by
  creating a Neon branch per run and deleting it afterwards.
- `tests/r2/` — mark tests `r2`, read the client and bucket from the
  `r2_test_bucket` fixture and a unique key from `r2_test_prefix`, and never
  from `R2_BUCKET_NAME`/`R2_ENDPOINT_URL`/etc. Reserve this marker for
  behaviour the existing stub cannot faithfully reproduce (presigned URLs
  actually fetched, multipart upload, conditional-write conflicts) —
  everything else (upload-then-list) stays on the existing stub. `moto` is
  not a dev dependency today (not listed in `pyproject.toml`); adopting it
  would be a dependency change, so that's an OPS task, not something to add
  ad hoc. CI supplies
  `R2_TEST_ENDPOINT_URL`, `R2_TEST_ACCESS_KEY_ID`, `R2_TEST_SECRET_ACCESS_KEY`
  (secrets) and `R2_TEST_BUCKET_NAME` (variable), pointing at a dedicated
  `greader-ci` bucket, plus a per-run `R2_TEST_PREFIX` cleaned up by
  `scripts/ci_r2_cleanup.py` after the run.

With those variables unset the marked tests skip themselves, so
`uv run pytest` stays green with no database or bucket — one command
everywhere. See `tests/conftest.py`.

## Definition of done

- endpoint under `/api/v1/`, visible in `/docs`
- `core/` free of FastAPI, ORM, and storage-client imports
- routes hold no business rules or SQL
- authorization lives in the service: every use case touching classroom data
  takes `actor: Actor` first and raises `PermissionDeniedError`; routes and
  pages never branch on a role (serializing one is fine). A handler gets the actor with
  `current_actor(request)`, never `Depends()`. Non-member → 404, wrong role
  in own Classroom → 403
- HTML pages live in `core/<slice>/pages.py` (no `/api` prefix); only
  `pages.py` renders templates. Templates live in
  `web/templates/<group>/<page-id>_<slug>.html`, group one of `shared`,
  `student`, `instructor`, `admin` (e.g. `student/s02_solve.html`)
- templates build buttons and inputs only through the macros in
  `web/templates/_components/forms.html`, and layout pieces (page header, tabs,
  badge, empty state, modal) through `_components/ui.html`; style with the
  tokens in `input.css`, then rebuild `app.css`
- every `<form method="post">` renders `{{ csrf_field() }}` (import the forms
  macros `with context`), and every POST page handler takes `csrf_token` and
  calls `require_csrf(request, csrf_token)` first (`core/auth/csrf.py`); the
  tests post forms through `tests/integration/forms.py`
- integration tests cover each page route for every role: 200 with the right
  template for the allowed role, 403/404 for the others
- unit test at the service/repository seam, integration test at the HTTP layer
- architecture tests pass
- `pytest`, `ruff check`, `ruff format --check` all pass
- if the PR touches anything under `src/`, it also adds or modifies something
  under `tests/` — a pre-existing suite staying green is not evidence the new
  code works, only that it wasn't exercised
- the PR description quotes the CI result for the PR's own head commit, not a
  number from a local run

## Git

Branch from `dev`, named `<type>/<TASK-ID>-<slug>` where type is `feat`, `fix`,
`chore`, `docs`, or `refactor`. Pull requests target `dev`, not `main` — `main`
is only this repo's default branch, so GitHub pre-fills it as the PR base;
change the base to `dev` before opening, every time. PRs need one approval.
Never commit directly to `main` or `dev`.

## Typing rules

These rules apply to every file under `src/` and `tests/`. `ruff`'s `ANN401`
only flags `Any` in argument annotations — `-> dict[str, Any]` passes it clean.
The actual enforcement is `tests/architecture/test_conventions.py`. **A rule
below without a matching test in that file is advisory, not binding** — when
you add a rule here, add its test in the same PR.

**No `Any`**

- Never import or use `typing.Any`, including `dict[str, Any]`, `list[Any]`, `Callable[..., Any]`.
- If you think you need `Any`, the contract has not been decided yet. Stop and ask in the PR.
- A service or repository must never return a bare `dict` from a public method. Return a
  domain object (dataclass). Converting to dict/JSON is the schema layer's job, at `routes`.

**`X | None` is allowed in exactly three cases**

1. A `Repository.get()` whose Protocol declares `X | None` (see `core/topics/ports.py`).
2. A domain field that is genuinely nullable, e.g. `artifact_id: str | None`.
3. An optional argument defaulting to `None` where the `None` case is handled explicitly
   on the following lines.

Anywhere else, `| None` is not allowed.

**Never use None as control flow**

- A service must not return `None` to mean "not found". Raise a domain error
  (`TopicNotFoundError`, `AssignmentNotFoundError`) and let `routes` translate it to HTTP.
- Never write `value or []`, `value or {}`, `value or 0` to paper over a `None`.
  If the field must not be empty, give the dataclass a `field(default_factory=list)`.
  If it can genuinely be empty, write `if value is None:` so the case is visible.
- Never write `getattr(obj, "field", [])` to dodge an AttributeError. If the attribute
  should exist, access it directly and let the test fail loudly instead of hiding it at runtime.

**Partial updates must not drop fields**

- A use case that updates part of an entity must load the existing entity and merge.
  Never build a fresh object from the request payload alone and hand it to `repository.update()`.
- Every adapter implementing the same Protocol must behave identically. If the in-memory
  adapter clears a relationship and the SQL adapter does not, that is a Protocol violation.
