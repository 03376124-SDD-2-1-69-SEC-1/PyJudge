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
| CORE-05 | นัด | `core/test_cases/`, `tests/` | linked to an assignment, deleted with it |
| CORE-06 | พาย | `database/storage.py`, config | file uploads to R2 through an endpoint |
| CORE-07 | นัด + โปรแกรม | `core/assignments/`, `web/templates/`, `core/assignments/routes.py` | assignment saved from an approved draft |
| FE-01 | โปรแกรม | `web/templates/base.html`, `web/static/css/input.css` | every page extends base |
| FE-02 | โปรแกรม | `web/templates/generate.html`, `core/generation/routes.py` | submit renders a draft from the mock |
| FE-03 | โปรแกรม | `web/templates/review.html`, `core/assignments/routes.py` | citations shown, approve and reject work |
| FE-04 | โปรแกรม | `web/templates/save.html`, `core/assignments/routes.py` | form matches the mockup |
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
| CORE-09 | พาย | `core/knowledge_documents/`, `database/core/knowledge_document_repository.py`, `tests/` | a citation's `document_id` resolves to the document's filename through Core |
| OPS-09 | พาย | `.github/`, `setup-branch-protection.sh`, `tests/conftest.py`, `tests/db/`, `pyproject.toml` pytest config, `.env.example`, `AGENTS.md`, `docs/task-scope.md` | CI runs `tests/db/` against a Neon branch it creates and deletes per run; the canary reports RUN, not SKIPPED |
| CORE-10 | พาย | `database/core/assignment_repository.py`, `tests/db/` | `create_test_case`, `list_test_cases`, `update_test_case`, `delete_test_case` implemented on `SQLAssignmentRepository`; a `postgres`-marked test proves a test case round-trips through real Postgres |
| OPS-10 | พาย | `.github/workflows/ci.yml`, `src/greader/r2_safety.py`, `scripts/ci_r2_cleanup.py`, `tests/r2/`, `tests/unit/test_r2_safety.py`, `tests/conftest.py`, `pyproject.toml`, `AGENTS.md`, `README.md` | `tests/r2/` runs in CI against the real `greader-ci` bucket, not skipped; presigned-URL fetch, multipart upload, and a conditional-write conflict are each proven against real R2 |
| OPS-11 | พาย | `docs/task-scope.md`, `AGENTS.md`, `pyproject.toml` | a row that owns a slice can mount it without an out-of-scope edit |
| CORE-11 | พาย | `src/greader/core/assignments/`, `tests/` | the domain layer holds no field that exists only to satisfy a table; the contract test covers parent/child containment |

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
