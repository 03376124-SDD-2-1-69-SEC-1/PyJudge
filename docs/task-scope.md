# Task scope

Maps a TASK-ID to who owns it, which paths it may touch, and what "done" means.
Read by `/grill-me`. Keep in sync with the team board.

| TASK-ID | Owner | May touch | Done when |
|---|---|---|---|
| OPS-* | พาย | anything | varies, see board |
| CORE-01 | พาย + ฟิล์ม | `core/generation/schemas.py` (both repos, identical) | `core/generation/schemas.py` exists in both repos and is byte-for-byte identical |
| CORE-02 | พาย | `core/generation/routes.py`, `ai/client.py` | mock endpoint callable from outside |
| CORE-03 | พาย | `core/topics/`, `tests/` | merged to dev and runs |
| CORE-04 | นัด | `core/assignments/`, `database/core/assignment_repository.py`, `tests/` | create, update, delete via API |
| CORE-05 | นัด | `core/test_cases/`, `database/core/test_case_repository.py`, `tests/` | linked to an assignment, deleted with it |
| CORE-06 | พาย | `database/storage.py`, config | file uploads to R2 through an endpoint |
| CORE-07 | นัด + โปรแกรม | `core/assignments/`, `web/templates/`, `core/assignments/routes.py` | assignment saved from an approved draft |
| FE-01 | โปรแกรม | `web/templates/base.html`, `web/static/css/input.css` | every page extends base |
| FE-02 | โปรแกรม | `web/templates/generate.html`, `core/generation/routes.py` | submit renders a draft from the mock |
| FE-03 | โปรแกรม | `web/templates/review.html`, `core/assignments/routes.py` | citations shown, approve and reject work |
| FE-04 | โปรแกรม | `web/templates/save.html`, `core/assignments/routes.py` | form matches the mockup |
| AI-01 | ฟิล์ม | ai repo: `app/`, `database/` | insert and query a sample vector |
| AI-02 | ฟิล์ม | ai repo: `ingestion/` | text extracted per page from the test files |
| AI-03 | พาย + ฟิล์ม | ai repo: `ingestion/chunking.py` | chunk boundaries match expectations on >=80% of test files |
| AI-04 | ฟิล์ม | ai repo: `ingestion/`, `embeddings/` | one PDF ingested end to end, chunks and vectors present |
| AI-05 | ฟิล์ม | ai repo: `retrieval/` | filtered query returns source_id, page, score |
| AI-06 | พาย | ai repo: `generation/` | draft and citations returned per the contract |
| AI-07 | ฟิล์ม | ai repo: `routes/knowledge.py` | deleting a document leaves no chunks behind |
| DES-02 | อุ้ม | ai repo: `tests/fixtures/pdfs/`, `docs/` | files present with a digital/scan table |
| DES-03 | อุ้ม | `docs/test-scenarios.md` | a checklist someone can follow |
| BUG-* | varies | whatever the fix needs, nothing more | the failing scenario passes |

## Off-limits regardless of task

Only an OPS task, assigned to พาย, may change:

- `alembic/` and anything that runs a migration
- `.env`, `.env.example`, credentials
- `database/core/tables.py`, `database/rag/tables.py`
- `pyproject.toml` dependencies
- CI config, `.gitignore`
