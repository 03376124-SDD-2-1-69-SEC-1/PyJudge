# GReader Team Scaffold Design

Status: approved direction, awaiting written-spec review  
Date: 2026-09-02

## Objective

Turn the current feature-heavy repository into a readable modular-monolith scaffold for a student team. The repository must contain one executable Core API example, clear ownership placeholders for unfinished features, one reusable server-rendered layout, and tests that preserve the architectural rules.

The scaffold must help a teammate answer three questions without reading unrelated code:

1. Where does my feature belong?
2. Which existing module demonstrates the expected API shape?
3. Which tests and commands prove my work is ready?

## Product and Team Scope

### Implemented reference

- `core/topics` is the only complete feature slice.
- It exposes JSON CRUD endpoints under `/api/v1/topics`.
- It stores state in a process-local in-memory repository.
- It appears in FastAPI's generated OpenAPI document and Swagger UI.
- Its tests demonstrate unit, repository-contract, and HTTP integration testing.

### Owned placeholders

- `core/assignments` belongs to the teammate implementing Assignment and Test Case behavior.
- `ai` belongs to the teammate implementing future AI behavior.
- Placeholder modules contain responsibility comments and acceptance criteria, but no executable feature behavior or solution-shaped pseudocode.
- The Assignment guide may refer to Topic and the repository pattern without prescribing the implementation.

### Shared web foundation

- The application serves one minimal page at `/`.
- `base.html` is the single global layout extension point.
- `home.html` extends `base.html` and demonstrates content blocks.
- Project-authored templates contain no script elements, JavaScript URLs, or inline event handlers.
- FastAPI's built-in `/docs` page is explicitly outside this restriction.
- Tailwind is consumed as compiled CSS. Browser runtime Tailwind and Node/npm are not introduced.

## Non-goals

- No Assignment CRUD implementation.
- No Test Case CRUD implementation.
- No Gemini provider, AI generation, RAG, embeddings, PDF ingestion, or artifact review.
- No database schema, migrations, SQLAlchemy adapter, PostgreSQL configuration, or persistence guarantee.
- No authentication, authorization, course management, document upload, analytics, or grading.
- No frontend JavaScript authored by the project.
- No compatibility path for the current AI database tables; the database owner will initialize a new schema later.

## Target Structure

```text
src/greader/
├── __init__.py
├── main.py                         # composition root only
├── core/
│   ├── __init__.py
│   ├── topics/                     # complete reference slice
│   │   ├── __init__.py
│   │   ├── models.py               # domain model
│   │   ├── schemas.py              # HTTP request/response models
│   │   ├── repository.py           # repository interface + memory adapter
│   │   ├── service.py              # use-case rules
│   │   └── routes.py               # FastAPI adapter
│   └── assignments/                # teammate-owned placeholder
│       ├── __init__.py
│       ├── README.md                # development guide and acceptance criteria
│       ├── models.py                # responsibility comments only
│       ├── schemas.py               # responsibility comments only
│       ├── repository.py            # responsibility comments only
│       ├── service.py               # responsibility comments only
│       └── routes.py                # responsibility comments only
├── ai/                              # teammate-owned placeholder
│   ├── __init__.py
│   └── README.md
├── persistence/
│   └── README.md                    # future single-schema ownership guide
└── web/
    ├── templates/
    │   ├── base.html
    │   └── home.html
    └── static/css/
        ├── input.css
        └── app.css

tests/
├── architecture/
│   ├── test_import_boundaries.py
│   └── test_no_browser_javascript.py
├── integration/
│   ├── test_topics_api.py
│   └── test_web.py
└── unit/core/topics/
    ├── test_repository.py
    └── test_service.py
```

## Dependency Direction

```text
main → web routes/templates
main → core.topics routes
core.topics routes → service → repository interface + domain
core.topics memory adapter → repository interface + domain
future ai → core domain
core ─X→ ai
```

`main.py` creates dependencies and registers routes. Domain and service modules do not import FastAPI. Core never imports AI. The future database adapter will depend on a Core repository interface; Core use cases will not depend on database technology.

## Topic API Contract

Topic is a reusable subject classification, such as arrays, graphs, or dynamic programming.

### Representation

- `id`: server-generated UUID string
- `name`: required, trimmed string from 1 to 80 characters
- `description`: optional trimmed string up to 500 characters

The API model is an example contract, not the future database schema.

### Endpoints

| Method | Path | Success | Failure |
|---|---|---:|---:|
| `POST` | `/api/v1/topics` | `201` with created Topic | `409` duplicate name |
| `GET` | `/api/v1/topics` | `200` with Topic list | — |
| `GET` | `/api/v1/topics/{topic_id}` | `200` with Topic | `404` unknown ID |
| `PUT` | `/api/v1/topics/{topic_id}` | `200` with replaced Topic | `404` unknown ID, `409` duplicate name |
| `DELETE` | `/api/v1/topics/{topic_id}` | `204` | `404` unknown ID |

Names are unique after trimming and case-folding. List order is deterministic by normalized name. Validation failures use FastAPI's standard `422` response. Domain conflicts use `{"detail": {"code": "topic_name_conflict"}}`; missing resources use `{"detail": {"code": "topic_not_found"}}`.

## Core Topic Components

### Domain model

Represents Topic independently from HTTP and storage. It contains no ORM or FastAPI types.

### HTTP schemas

Separate create, replace, and response models keep generated OpenAPI documentation explicit. They translate at the route boundary.

### Repository interface and adapter

The repository interface is the future database seam. The in-memory adapter is the only current implementation and owns no business validation beyond storage mechanics.

### Service

The service owns normalization, uniqueness, not-found behavior, and generated IDs. Routes translate service errors into HTTP responses.

### Routes

Routes parse HTTP input, call one service operation, and return an HTTP response. They contain no storage access and no business branching beyond error translation.

## Assignment Placeholder Guide

The Assignment package is import-safe but behavior-free. Each module starts with a module docstring and short comments describing its responsibility:

- `models.py`: define Assignment as the owner of Test Cases using the glossary in `CONTEXT.md`.
- `schemas.py`: define API contracts only after the teammate agrees on the use cases.
- `repository.py`: define a persistence seam from real service needs; do not copy database shapes into the domain.
- `service.py`: implement use cases and domain rules without FastAPI or database imports.
- `routes.py`: expose versioned HTTP adapters and keep business rules out of routes.

`core/assignments/README.md` gives the teammate a development sequence, test expectations, dependency rules, and completion checklist. It does not include function bodies or pseudocode that solves the assignment.

## AI Placeholder Guide

`ai/README.md` states that AI is part of the same monolith but is not implemented. Future AI code may import stable Core domain models. Core packages must not import AI. No provider dependency, configuration, database records, routes, templates, or smoke scripts remain.

## Persistence Placeholder Guide

`persistence/README.md` records that the database owner will initialize one Core schema later. It explains the adapter direction and migration expectations without defining tables. Until then, application state resets on process restart.

## Application and Web Flow

`create_app` accepts an optional Topic repository so tests can create isolated applications. The default application creates one in-memory repository, one Topic service, registers the Topic router, mounts compiled CSS, and registers the home page.

The home page explains which modules are implemented and which are placeholders, and links to `/docs`. It does not simulate unfinished features.

## Testing Strategy

### Unit tests

- In-memory repository create/read/list/replace/delete behavior.
- Topic service normalization, uniqueness, stable errors, and not-found behavior.
- Each test creates isolated state.

### Integration tests

- Every Topic endpoint and status code.
- OpenAPI includes all Topic operations.
- A fresh application starts empty.
- The home page renders through `base.html` and links to Swagger.

### Architecture tests

- Scan every project-authored HTML template for script elements, JavaScript URLs, and inline event-handler attributes.
- Exclude FastAPI-generated `/docs` because it is framework-owned developer tooling.
- Core source files may not import `greader.ai`.
- Placeholder Assignment modules remain importable.
- The application can boot without database or AI packages.

### Verification commands

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Dependencies and Cleanup

Remove `google-genai`, Alembic, SQLAlchemy, Psycopg, multipart support, and Pydantic Settings. Keep FastAPI, Uvicorn, Jinja2, and the existing test/lint tools.

Keep `input.css` as the Tailwind source and commit compiled `app.css`. Document the Tailwind standalone-CLI command; do not require Node/npm or a browser runtime. Automated tests do not require the standalone binary.

Remove the current AI implementation, Assignment implementation, database models, migrations, seed scripts, AI templates, feature tests, database container wiring, and stale navigation. Preserve unrelated user-owned files and changes.

## Documentation and Ownership

### README

The root README must show:

- exact project status: Topic API implemented; Assignment, AI, and persistence are placeholders;
- target tree and dependency direction;
- setup, run, Swagger, test, lint, and Tailwind workflow;
- no-script scope and Swagger exception;
- how to replace the in-memory adapter later.

### Agent guidance

Replace outdated AI implementation guidance with root `AGENTS.md`. Agents must read `CONTEXT.md`, ADRs, `plan.md`, and the target module README before editing. The file defines ownership boundaries, prohibited scope, required verification, and the rule against implementing another teammate's placeholder without an explicit task.

### Team plan

Rewrite stale `plan.md` as a workstream table:

- Foundation owner: application composition, layout, architecture guards.
- Reference API owner: Topic CRUD and tests.
- Assignment owner: implement Assignment/Test Case from its module guide.
- AI owner: define and implement AI only after Assignment contracts stabilize.
- Database owner: design one Core schema and add adapters/migrations later.
- Design owner: update `base.html` and shared CSS so all future pages inherit changes.

Each workstream includes prerequisites, owned files, deliverables, prohibited overlap, and verification commands suitable for a human or coding agent.

## Acceptance Criteria

1. A clean checkout installs and starts without a database or AI key.
2. `/` renders the shared layout; project templates contain no authored JavaScript.
3. `/docs` displays the five Topic CRUD operations.
4. Topic CRUD works entirely in memory and resets after application restart.
5. Assignment and AI contain guidance only and expose no feature routes.
6. No AI, SQLAlchemy, Alembic, database schema, or migration implementation remains.
7. Tests enforce API behavior, import direction, and the no-script rule.
8. README, `AGENTS.md`, `CONTEXT.md`, ADRs, and `plan.md` agree on status and ownership.
9. The repository passes the full test and Ruff checks.
10. Changes are committed atomically and pushed to the configured `origin` after verification.

## Rollout

No existing runtime data or schema is preserved. The refactor replaces the current implemented AI/Assignment application with the agreed team scaffold. The database owner later introduces schema and adapters as a separate reviewed workstream.
