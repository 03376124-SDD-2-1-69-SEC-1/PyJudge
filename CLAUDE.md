# GReader

GReader is a scaffold for a system that helps Instructors prepare programming assignments, evaluation examples, and related data.

Built as a **modular monolith** with FastAPI and Jinja2. Every module lives in one app, but responsibilities and ownership are split cleanly so each team member can work their slice without tight coupling to the rest.

> Current status: team scaffold, not a finished system.
>
> Only the Topics API is fully working. Assignment, AI, and Database are owner-team workspaces.

Team members should be able to answer these three questions from this file alone, without reading unrelated code:

1. Which module owns the feature I'm responsible for?
2. Which module is the reference for the API pattern and layering the team expects?
3. Which tests and commands prove my work is ready to ship?

## Ownership

| Area | Status | Owner |
|---|---|---|
| `core/topics` | Working CRUD reference API | Foundation / Reference API |
| `core/assignments` | Placeholder, awaiting design | Assignment team |
| `ai` | Placeholder, waiting on a stable Assignment contract | AI team |
| `database` | Placeholder, awaiting schema design | Database owner |
| `web/templates/base.html` | Shared layout for every page | Design team |

Never implement another team's placeholder without being assigned to it — each area is deliberately left for its owner to design the contract and implementation.

## Out of scope

To keep each team owning its own design, the scaffold deliberately **excludes**:

- Assignment and Test Case CRUD
- AI generation, provider integration, RAG, embeddings, PDF ingestion
- Database schema, migrations, ORM, or storage guarantees
- Authentication, authorization, course management, document upload, analytics, grading
- Browser JavaScript authored by the team
- Compatibility with schemas or data from earlier AI/database implementations

None of this is forgotten — each item is future work that starts from its owner team's contract or task, not from this scaffold.

## Terminology

Use these terms consistently across code, API, docs, and screens.

| Term | Meaning | Don't use |
|---|---|---|
| **Instructor** | Creates and maintains programming assignments | Teacher, Admin, User |
| **Assignment** | A programming problem: description, constraints, and Test Cases | Challenge, Task, Question |
| **Test Case** | An input/expected-output pair, always owned by an Assignment | Example, Check |
| **Topic** | A knowledge area an Assignment can reference (Array, Graph, Dynamic Programming) | Tag, Category, Label |

## Stack

- Python 3.12+
- FastAPI (HTTP API)
- Jinja2 (HTML templates)
- Uvicorn (app server)
- uv (dependency + venv management)
- Pytest (tests)
- Ruff (lint + format)
- Tailwind CSS (styling)

No database client, ORM, migration tool, AI provider, or external service dependency exists yet.

## Local setup

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run fastapi dev src/greader/main.py
```

| URL | Purpose |
|---|---|
| <http://127.0.0.1:8000/> | Sample page using the shared layout |
| <http://127.0.0.1:8000/health> | Liveness check |
| <http://127.0.0.1:8000/docs> | Swagger UI |
| <http://127.0.0.1:8000/openapi.json> | OpenAPI spec |
| <http://127.0.0.1:8000/api/v1/topics> | Topics API |

Stop the server with `Ctrl+C`.

## Project structure

```text
greader/
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile
│
├── docs/
│   └── adr/
│       ├── 0001-reset-to-core-schema.md
│       ├── 0002-use-topics-as-the-reference-slice.md
│       └── 0003-use-neon-and-r2-for-future-database.md
│
├── src/greader/
│   ├── main.py
│   ├── ai/
│   │   └── README.md
│   │
│   ├── core/
│   │   ├── topics/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   └── routes.py
│   │   │
│   │   └── assignments/
│   │       ├── README.md
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── repository.py
│   │       ├── service.py
│   │       └── routes.py
│   │
│   ├── database/
│   │   └── README.md
│   │
│   └── web/
│       ├── templates/
│       │   ├── base.html
│       │   └── home.html
│       └── static/css/
│           ├── input.css
│           └── app.css
│
└── tests/
    ├── architecture/
    ├── integration/
    └── unit/
```

### Project-level files

| File | Purpose |
|---|---|
| `README.md` | Overview, quickstart, structure, terminology, ownership, core rules |
| `pyproject.toml` | Dependencies and Pytest/Ruff/Coverage config |
| `uv.lock` | Locked dependency versions for reproducible installs |
| `Dockerfile` | Production container build |
| `docs/adr/` | Architecture decisions that must not change without team discussion |

### `src/greader/main.py`

`main.py` is the **composition root**. Its only job is wiring the app together:

- create the FastAPI application
- mount static files
- configure Jinja2 templates
- construct repositories and services
- store services on application state
- include the API router
- declare app-level routes (`/`, `/health`)

No business rule, SQL, database operation, or AI workflow belongs in this file.

`create_app()` accepts an externally supplied repository, so tests can build an app with isolated state.

## Core module architecture

Topics is the reference implementation other Core modules should follow.

```text
HTTP request
    ↓
routes.py
    ↓
service.py
    ↓
repository interface
    ↓
in-memory or database adapter
```

| File | Responsibility | Must not contain |
|---|---|---|
| `models.py` | Domain model and business vocabulary | FastAPI, ORM, storage client |
| `schemas.py` | Request/response schemas shown in OpenAPI | Business workflow |
| `repository.py` | Read/write interface, plus adapters | HTTP handling |
| `service.py` | Use cases and business rules | FastAPI, ORM, SQL |
| `routes.py` | Accept HTTP requests, call the service, map errors to HTTP responses | Business rules or SQL |

Dependencies flow from adapter toward domain — the domain never knows about the framework or the database.

### Dependency direction

```text
main → web templates/static files
main → core.topics routes
core.topics routes → service → repository interface + domain
in-memory adapter → repository interface + domain
future AI → Core domain
Core ─X→ AI
future database adapter → Core repository interface
Core service ─X→ database technology
```

`main.py` composes dependencies and registers routes. Domain and service code must never know about FastAPI, an ORM, or storage technology.

## Topics API

CRUD reference that runs with no database.

| Method | Path | Meaning | Success |
|---|---|---|---|
| `POST` | `/api/v1/topics` | Create a Topic | `201` |
| `GET` | `/api/v1/topics` | List all Topics | `200` |
| `GET` | `/api/v1/topics/{topic_id}` | Get one Topic | `200` |
| `PUT` | `/api/v1/topics/{topic_id}` | Replace a Topic | `200` |
| `DELETE` | `/api/v1/topics/{topic_id}` | Delete a Topic | `204` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/topics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Graphs",
    "description": "Network problems"
  }'
```

Topic rules:

- `name` must not be empty
- `name` max 80 characters
- `description` max 500 characters
- leading/trailing whitespace is trimmed
- `name` must be unique, case-insensitive
- `PUT` replaces the whole record — not a partial update
- listings are sorted by name
- IDs are UUIDs

Errors the service maps to HTTP responses:

| Situation | Status | Error code |
|---|---|---|
| Topic not found | `404` | `topic_not_found` |
| Duplicate Topic name | `409` | `topic_name_conflict` |
| Request fails schema validation | `422` | FastAPI validation error |

Topic data lives in process memory — it's lost on restart and is not the real database contract.

## Assignment module

Start at `src/greader/core/assignments/README.md`.

Still a placeholder: every file only describes its intended responsibility. No working model, schema, CRUD, or route yet.

Recommended order:

1. Agree the Assignment + Test Case use cases and API contract
2. Define the domain model, with Assignment owning its Test Cases
3. Derive repository operations from the required use cases
4. Write the service and business rules
5. Write request/response schemas
6. Add routes under `/api/v1/`
7. Start with an in-memory adapter
8. Write unit and integration tests
9. Let the Database owner add the database adapter later

Design business rules in the service, not the database schema. Assignment must not import AI.

## AI module

Start at `src/greader/ai/README.md`.

No feature, provider, route, database record, or configuration yet.

Start once the Assignment domain contract is stable:

1. Nail the use case before picking an AI provider
2. AI may import Core domain models
3. Core must never import `greader.ai`
4. Put a provider behind an interface so providers can be swapped
5. Use a fake provider in tests
6. Automated tests must never call a real provider

```text
Allowed:  AI → Core domain
Forbidden: Core → AI
```

## Database module

Start at `src/greader/database/README.md`.

No schema, migration, credentials, or database adapter yet.

Agreed direction:

```text
FastAPI → Neon PostgreSQL   for structured data
FastAPI → Cloudflare R2     for PDFs and uploaded objects
```

The database stores only object keys and file metadata — actual files live in R2.

When database work starts:

1. Database owner designs one Core schema
2. Migrations come after the schema is agreed
3. Add the adapter behind the Core module's repository interface
4. Service keeps depending on the repository interface, unchanged
5. Handle connections and credentials at the system edge
6. Core service must never import an ORM or storage client directly

Choosing Neon and R2 sets future direction — it does not authorize adding schema, clients, migrations, or credentials without a task.

## Web and Design

Shared layout: `src/greader/web/templates/base.html`. Other pages use Jinja inheritance:

```jinja2
{% extends "base.html" %}
```

`base.html` owns shared elements: HTML document structure, `<head>`/metadata, global stylesheet, header/navigation, the central content block.

Design team edits the shared layout in one place (`base.html`); other pages inherit from it.

### Tailwind CSS

Edit the source at `src/greader/web/static/css/input.css`, then compile to `src/greader/web/static/css/app.css`:

```bash
tailwindcss \
  -i src/greader/web/static/css/input.css \
  -o src/greader/web/static/css/app.css \
  --minify
```

Requires the Tailwind standalone CLI (not set up automatically in this repo). No Node/npm involved. Edit `input.css` and regenerate `app.css` — don't hand-edit the compiled CSS.

### JavaScript constraint

Team-authored HTML templates must stay free of:

- `<script>` elements
- `javascript:` URLs
- inline event handlers (`onclick`, `onload`, `onchange`, ...)

`/docs` (Swagger) uses its own internal JavaScript — that's developer tooling, not a project-authored template, so it's exempt. An architecture test enforces this rule automatically.

## Tests

```text
tests/
├── architecture/
├── integration/
└── unit/
```

- **`tests/unit/`** — domain rules, service, repository, without HTTP.
- **`tests/integration/`** — FastAPI through the ASGI transport, no real server or external service.
- **`tests/architecture/`** — guards key rules: Core must not import AI, the Assignment placeholder must still be importable, team-authored templates must carry no browser JavaScript.

## Quality gate

Run before every commit or PR:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Current scaffold status: `12 tests passed`, Ruff check passed, Ruff format check passed.

If format check fails:

```bash
uv run ruff format .
```

Then rerun all three quality-gate commands.

## Where to start by role

**Assignment owner** — start at `src/greader/core/assignments/README.md`, then read `core/topics` for structural pattern. Design Assignment's own use case before reusing any Topic domain rule.

**AI owner** — start at `src/greader/ai/README.md`. Wait for a stable Assignment contract before building integrations that depend on it.

**Database / Storage owner** — start at `src/greader/database/README.md`, `docs/adr/0001-reset-to-core-schema.md`, `docs/adr/0003-use-neon-and-r2-for-future-database.md`. Add schema or migrations only after a task exists and the Core schema is agreed.

**Web / Design** — start at `src/greader/web/templates/base.html` and `src/greader/web/static/css/input.css`. Keep Jinja inheritance intact and stay free of browser JavaScript.

**Understanding the backend pattern** — read in this order to see domain and use case before HTTP detail:

```text
core/topics/models.py
→ core/topics/repository.py
→ core/topics/service.py
→ core/topics/schemas.py
→ core/topics/routes.py
→ main.py
→ tests/
```

## Adding a new feature

1. Confirm which team owns the feature
2. Read that module's ADRs and README
3. Write the use case and public contract clearly
4. Define the domain model, free of FastAPI or database coupling
5. Derive the repository interface from what the service needs
6. Write the service and business rules
7. Write HTTP schemas and routes under `/api/v1/`
8. Wire dependencies in `main.py`
9. Write unit tests at the service/repository seam
10. Write integration tests at the HTTP/OpenAPI layer
11. Run the quality gate
12. Update the README, module guide, and ownership table when scope changes

## Guardrails

- Implement another team's placeholder only when assigned to it
- Keep business rules out of routes and `main.py`
- Keep domain and service code free of FastAPI imports
- Keep Core free of AI imports
- Keep service code free of ORM, SQL, or storage-client imports
- Add database schema or migrations only against a task
- Treat the in-memory Topic model as a demo, not an agreed database schema
- Keep new APIs under `/api/v1/`
- Keep automated tests off real databases and real AI providers
- Keep browser JavaScript out of team-authored templates
- Keep credentials, API keys, and connection strings out of commits
- Edit Tailwind source and rebuild rather than hand-editing `app.css`
- Update OpenAPI tests and docs whenever a public contract changes

## ADRs

`docs/adr/` records the reasoning behind key decisions:

- `0001-reset-to-core-schema.md` — no legacy schema or migrations carried over; stay in-memory until the Database owner designs the Core schema
- `0002-use-topics-as-the-reference-slice.md` — Topics is the one executable reference slice
- `0003-use-neon-and-r2-for-future-database.md` — Neon for structured data, R2 for object storage, as future direction

Changing these decisions requires team agreement and an ADR update — not a silent implementation change.

### New-file policy

`.gitignore` ignores all new files outside the agreed scope, except `README.md`, `.env.example`, and `.gitignore` itself. Files Git already tracks stay tracked until explicitly removed from the index.

## Definition of Done

A task is done when:

- the API lives under `/api/v1/`
- the public contract shows up in Swagger/OpenAPI
- domain and service code don't depend on FastAPI, an ORM, or a storage client
- routes carry no business rule or SQL
- unit tests cover the service/repository seam
- integration tests cover the HTTP endpoint
- tests call no real external provider or database
- architecture tests still pass
- docs and the ownership table are current
- `pytest`, Ruff lint, and Ruff format check all pass

## Scaffold acceptance criteria

The scaffold is ready when:

1. a fresh clone installs and starts with no database or AI key
2. `/` renders the shared layout, and team-authored templates carry no JavaScript
3. `/docs` shows all five Topic CRUD operations
4. Topic CRUD works in memory and resets on app restart
5. Assignment and AI expose guidance only, no feature routes
6. no out-of-scope AI, SQLAlchemy, Alembic, database schema, or migration implementation exists
7. tests guard API behavior, import direction, and the no-browser-JavaScript rule
8. `README.md` and ADRs describe status and ownership that match the code
9. Pytest and Ruff quality gates pass

## Migration note

The scaffold makes no promise to preserve runtime data or an existing schema. The Database owner will add the Core schema and adapters later, as a separate reviewed workstream. Until then, application state stays in-memory only.
