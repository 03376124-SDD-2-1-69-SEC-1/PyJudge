# Handoff: Questly now persists to the real database (OPS-15, merged 2026-10-01)

Every classroom slice (auth, classrooms, assignments + Versions + Postings, submissions, drafts + daily Quota, document catalog, classroom stats) now reads and writes Postgres. `src/questly/main.py` wires a SQL adapter for every port; the old `PendingRepository` / 503 path is gone. Treat every write as permanent shared data.

## Where things are

- Schema: `src/questly/database/core/tables.py`, migration `alembic/versions/c4e8a2f17b90_ops_15_classroom_schema.py` (head).
- Why the schema looks the way it does: `docs/adr/0008-ops-15-schema.md` (amends ADR-0007 "Schema changes"). Read it before touching a table or an adapter.
- SQL adapters: `src/questly/database/core/*_repository.py`. Copy `topic_repository.py`'s shape: one session per method, `_to_domain` mapping, KeyError on unknown update, None from get, bool from delete.
- Classroom card numbers: `src/questly/core/classrooms/stats.py` (`ComputedClassroomStats`, built on ports only).

## The database

- `.env` `DATABASE_URL` points at Neon project `greader` (`fancy-firefly-17960143`), branch `production`. The team calls it "dev". It holds real rows now.
- Existing accounts (all verified): `admin@kmitl.ac.th` (admin, id 5), `instructor@kmitl.ac.th` (instructor, id 6), plus walkthrough accounts `ops15.instructor@kmitl.ac.th` (instructor) and `65019999@kmitl.ac.th` (student) with one Classroom, Assignment, Posting and Submission. Keep them.
- Schema changes go through an OPS task owned by พาย: a new hand-written migration plus an ADR-0008-style entry. Ask instead of editing `tables.py` or `alembic/`.

## Changing an adapter or a port

Every port has one contract that the fake and the SQL adapter both pass:

1. `tests/contracts/<slice>_repository.py`: the behaviour, written once.
2. `tests/unit/core/<slice>/test_*_contract.py`: binds it to the fake in `tests/fakes/`.
3. `tests/db/test_<slice>_repository.py`: binds it to the SQL adapter (`pytestmark = pytest.mark.postgres`, mixes in `tests.db.rows.RealRows` so foreign keys get real parent rows).

Change behaviour by editing the contract first, then make both adapters pass it. The fake and the SQL adapter stay identical (AGENTS.md "Partial updates must not drop fields").

## Running database tests

- `tests/db` truncates every `core` table before and after each test. Point it only at a throwaway Neon branch, through `POSTGRES_TEST_URL`. `tests/conftest.py` refuses a URL whose host matches `DATABASE_URL`.
- A throwaway branch exists: `ops15-test`. Run the suite with the DSN inlined so it never prints: `POSTGRES_TEST_URL="$(neonctl connection-string ops15-test --project-id fancy-firefly-17960143 | sed -E 's#^postgres(ql)?://#postgresql+psycopg://#')" uv run pytest tests/db`
- `uv run pytest` alone skips `tests/db`; CI runs them on its own Neon branch.

## Running the app

- Start the server with `uv run uvicorn questly.main:app --reload`. The AGENTS.md command `uv run fastapi dev src/questly/main.py` cannot find the lazily built `app`; that is a known open bug.
- Demo mode (`uv run python -m scripts.demo`) still runs on in-memory fakes, never on the database.

## Mappings that surprise people

- Domain flags are timestamps in the table: `email_verified` ↔ `email_verified_at`, `revoked` ↔ `revoked_at`, `used` ↔ `used_at`, `archived` ↔ `archived_at` (set `now()` when the flag turns on).
- `users.full_name` (VARCHAR 120); `test_cases.kind` (sample/hidden/edge) and `note` (empty string stored as NULL).
- A Draft's content, citations and settings are JSONB on `core.drafts`; the daily Quota counts rows in `core.generation_events` since Bangkok midnight.
- A Submission stores its own `max_score`; classroom and assignment come from its Posting. Unposting deletes the Posting's Submissions (CASCADE).
- Per-Submission score is floored; averages round half up (`core/rounding.py`).

## Known gaps (each belongs to its own task)

- CORE-19: no Admin approve endpoint yet; making someone an Instructor takes a SQL `UPDATE` on `core.users.role` plus the matching `core.instructor_requests` row.
- CORE-16: `knowledge_documents.uploaded_by` is nullable and the upload code does not record the uploader; the T-03 picker lists only `ready` Documents of their uploader, so it stays empty until ingestion (AI-02 to 07) and the uploader land.
- Production `CodeRunner` is a stub: every test is `runtime_error`, every score 0 (ADR-0007 open question 1).
- Production `GenerationClient` is a stub: every Draft is "Sample Assignment".
- The `GenerationRepository` port has no production adapter; it is kept until someone retires it (ADR-0008).
