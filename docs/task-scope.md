# Task scope

Maps a TASK-ID to who owns it, which paths it may touch, and what "done" means.
Read by `/grill-me`. Keep in sync with the team board.

This is a single repo. "ai repo" in this table resolves to `src/greader/ai/`.

| TASK-ID | Owner | May touch | Done when |
|---|---|---|---|
| OPS-* | พาย | anything | varies, see board |
| CORE-01 | พาย + ฟิล์ม | `src/greader/core/generation/schemas.py` | `core/generation/schemas.py` exists once in this repo. Done — merged in PR #3 |
| CORE-02 | พาย | `core/generation/routes.py`, `ai/client.py` | mock endpoint callable from outside. Done — merged in PR #4 |
| CORE-03 | พาย | `core/topics/`, `tests/` | merged to dev and runs |
| CORE-04 | นัด | `core/assignments/`, `tests/` | create, update, delete via API |
| CORE-05 | นัด | `core/assignments/testcase_routes.py`, `tests/` | linked to an assignment, deleted with it |
| CORE-06 | พาย | `database/storage/r2.py`, config | file uploads to R2 through an endpoint |
| CORE-07 | นัด + โปรแกรม | `core/assignments/`, `web/templates/`, `core/assignments/routes.py` | Closed — superseded by ADR-0007: publishing a Draft is CORE-15 (`POST /api/v1/drafts/{id}/publish`), its page is FE-08 |
| FE-01 | โปรแกรม | `web/templates/base.html`, `web/static/css/input.css` | every page extends base |
| FE-02 | โปรแกรม | `web/templates/generate.html`, `core/generation/routes.py` | Closed — superseded by ADR-0007: T-03 generate page, see FE-08 |
| FE-03 | โปรแกรม | `web/templates/review.html`, `core/assignments/routes.py` | Closed — superseded by ADR-0007: T-04 review stepper, see FE-08 |
| FE-04 | โปรแกรม | `web/templates/save.html`, `core/assignments/routes.py` | Closed — superseded by ADR-0007: T-04 steps 3–4, see FE-08 |
| AI-01 | ฟิล์ม | `ai/` (domain and service, no ORM), `database/rag/vector_repository.py`, `tests/unit/ai/`, `tests/db/` | a vector inserted through the API comes back from a search, proven by a `postgres`-marked test against a real database |
| AI-02 | ฟิล์ม | ai repo: `ingestion/` | text extracted per page from the test files |
| AI-03 | พาย + ฟิล์ม | ai repo: `ingestion/chunking.py` | chunk boundaries match expectations on >=80% of test files |
| AI-04 | ฟิล์ม | ai repo: `ingestion/`, `embeddings/` | one PDF ingested end to end, chunks and vectors present |
| AI-05 | ฟิล์ม | ai repo: `retrieval/` | filtered query returns source_id, page, score |
| AI-06 | พาย | ai repo: `generation/` | draft and citations returned per the contract |
| AI-07 | ฟิล์ม | ai repo: `routes/knowledge.py` | deleting a document leaves no chunks behind |
| DES-02 | อุ้ม | ai repo: `tests/fixtures/pdfs/`, `docs/` | files present with a digital/scan table |
| DES-03 | อุ้ม | `docs/test-scenarios.md` | a checklist someone can follow |
| BUG-* | varies | whatever the fix needs, nothing more | the failing scenario passes |
| OPS-08 | พาย | `docs/task-scope.md`, `AGENTS.md`, `docs/adr/`, `.gitignore` | the table matches the tree; every done-condition is checkable in one repo |
| CORE-08 | พาย + ฟิล์ม | `core/generation/schemas.py`, `ai/client.py`, `tests/unit/ai/test_client.py`, `tests/integration/test_generation_api.py` | a citation identifies its source document; an approved draft has a stable handle; invalid input is rejected |
| CORE-09 | พาย | `core/uploads/`, `database/core/knowledge_document_repository.py`, `tests/` | a citation's `document_id` resolves to the document's filename through Core |
| OPS-09 | พาย | `.github/`, `setup-branch-protection.sh`, `tests/conftest.py`, `tests/db/`, `pyproject.toml` pytest config, `.env.example`, `AGENTS.md`, `docs/task-scope.md` | CI runs `tests/db/` against a Neon branch it creates and deletes per run; the canary reports RUN, not SKIPPED |
| CORE-10 | พาย | `database/core/assignment_repository.py`, `tests/db/` | test cases round-trip through `SQLAssignmentRepository.create`/`update`/`delete` as part of the assignment aggregate (see CORE-11); a `postgres`-marked test proves it in `tests/db/test_assignment_repository.py`. Done — see refactor/OPS-12-real-persistence |
| OPS-10 | พาย | `.github/workflows/ci.yml`, `src/greader/database/storage/safety.py`, `scripts/ci_r2_cleanup.py`, `tests/r2/`, `tests/unit/test_r2_safety.py`, `tests/conftest.py`, `pyproject.toml`, `AGENTS.md`, `README.md` | `tests/r2/` runs in CI against the real `greader-ci` bucket, not skipped; presigned-URL fetch, multipart upload, and a conditional-write conflict are each proven against real R2 |
| OPS-11 | พาย | `docs/task-scope.md`, `AGENTS.md`, `pyproject.toml` | a row that owns a slice can mount it without an out-of-scope edit |
| CORE-11 | พาย | `src/greader/core/assignments/`, `tests/` | the domain layer holds no field that exists only to satisfy a table; the contract test covers parent/child containment |
| OPS-12 | พาย | anything | wired Assignments/Topics/Uploads to real Postgres and R2; removed every in-memory adapter from src/; fixed a pre-existing SQLModel mapper bug in tables.py. Done — see refactor/OPS-12-real-persistence. |
| OPS-13 | พาย | `core/generation/__init__.py`, `core/generation/service.py`, `database/core/generation_repository.py`, `tests/fakes/generation.py`, `tests/contracts/generation_repository.py`, `tests/db/test_generation_repository.py`, `tests/db/conftest.py`, `tests/unit/core/generation/test_generation_repository_contract.py`, `tests/unit/core/generation/test_generation_service.py` | `__init__.py` no longer re-exports schema types under domain names; the JSON codec is public and shared by both adapters; a contract test proves the fake and SQL adapter round-trip identically; `generate()` marks a request failed if `create_artifact` raises, not only if the client call does |
| OPS-14 | พาย | `docs/adr/0007-classroom-centric-flow.md`, `CONTEXT.md`, `AGENTS.md`, `docs/task-scope.md`, `docs/wireframes/`, `tests/architecture/`; phase 2: `src/greader/core/`, `src/greader/integrations/`, `src/greader/database/pending.py`, `src/greader/web/templates/`, `src/greader/main.py`, `scripts/demo.py`, `tests/` | ADR-0007 accepted; every new AGENTS.md rule has a test in `tests/architecture/`; every route in the ADR's page and API contract exists on in-memory fakes and is covered by an integration test per role |
| OPS-15 | พาย | `database/core/tables.py`, `database/rag/tables.py`, `alembic/versions/`, `database/core/*_repository.py`, `tests/db/` | the ADR-0007 "Schema changes" list is one hand-written migration that CI upgrades on its own Neon branch; each new slice has a SQL adapter passing its contract test; no new-slice handler returns 503 |
| CORE-12 | TBD | `core/auth/`, `tests/` | sign-up (KMITL email only, faculty on instructor requests), verify (24 h link), login, logout, `current_actor(request)`; stdlib scrypt + server-side session; every `/api/v1/auth/*` endpoint in ADR-0007 has unit + integration tests |
| CORE-13 | TBD | `core/classrooms/`, `tests/` | create, join by code, regenerate/disable code, remove Member, archive/unarchive, summary + CSV; non-member gets 404, Student on instructor use case gets 403, proven by tests |
| CORE-14 | TBD | `core/assignments/`, `tests/` | Postings (per-Classroom deadline, max score, late, resubmit, close) and immutable Versions with a required reason; editing extends only the chosen Postings' deadlines; Test Cases carry `kind` and `note` |
| CORE-15 | TBD | `core/generation/`, `tests/` | Drafts per Classroom, stepper saves per step, regenerate one part, publish to many Classrooms through `AssignmentPublisher`; daily Quota charged on success only; `/api/v1/generations` removed |
| CORE-16 | TBD | `core/uploads/` → `core/documents/`, `tests/` | slice renamed; `/api/v1/documents` lists an Instructor's own library with "used in" counts, retry and delete; `/api/v1/uploads` removed. The import fix in `database/core/knowledge_document_repository.py` is พาย's |
| CORE-17 | TBD | `core/submissions/`, `src/greader/integrations/judge0.py`, `tests/` | Submit judges synchronously through `CodeRunner` and stores per-test results; Run judges sample tests and stores nothing; Late and Closed follow ADR-0007 §5; counted Submission = latest |
| CORE-18 | TBD | `core/notifications/`, `src/greader/integrations/email.py`, `tests/` | stored notifications (Assignment updated/published, Notify students) with read/read-all; "deadline tomorrow" computed on read; `EmailSender` stub used by auth and notifications |
| CORE-19 | TBD | `core/admin/`, `tests/` | approve/reject Instructor requests, list/search/deactivate users, AI settings (model from config allowlist, daily quota, max pages, require citations), six-service status |
| FE-05 | TBD | `web/templates/shared/g*`, `core/auth/pages.py`, `web/static/css/input.css` | G-01, G-03, G-04 with every lettered state, and the G-02 header partial, match the prototype with no JavaScript |
| FE-06 | TBD | `web/templates/shared/c*`, `core/classrooms/pages.py`, `web/static/css/input.css` | C-01 (both roles, empty states), C-02 and C-03 as `popover` modals match the prototype |
| FE-07 | TBD | `web/templates/student/`, `core/classrooms/pages.py`, `core/submissions/pages.py`, `web/static/css/input.css` | S-01 and S-02 with every lettered state match the prototype; Run and Submit are two buttons of one form |
| FE-08 | TBD | `web/templates/instructor/`, `core/*/pages.py` of classrooms, assignments, generation, documents, `web/static/css/input.css` | T-01…T-06 with every lettered state match the prototype; tabs are URLs; stepper steps are separate form posts |
| FE-09 | TBD | `web/templates/admin/`, `core/admin/pages.py`, `web/static/css/input.css` | A-01 three tabs and 01a/01b match the prototype; System status refreshes with `<meta http-equiv="refresh" content="60">` |

## The composition root

`src/greader/main.py` wires the application together, so a slice cannot reach
its own API without it. Any row whose done-condition names an endpoint may
therefore edit `main.py` without that path being listed in its "May touch"
column, and only to:

- import its own repository, service, and router
- add its own `create_app` keyword argument for the repository
- build the repository and service, and put the service on `application.state`
- call `application.include_router` for its own router

Nothing else in `main.py`: no business rules, and no touching another slice's
wiring. Copy the shape `core/topics` already uses there.

## Off-limits regardless of task

Only an OPS task, assigned to พาย, may change:

- `alembic/` and anything that runs a migration
- `.env`, `.env.example`, credentials
- `database/core/tables.py`, `database/rag/tables.py`
- `pyproject.toml` dependencies
- CI config, `.gitignore`
