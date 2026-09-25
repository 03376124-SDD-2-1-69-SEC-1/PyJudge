> **Historical.** Written for OPS-12 (2026-09) and not kept up to date. For the
> current state read `AGENTS.md`, `docs/task-scope.md` and
> `docs/handoff/2026-09-24-OPS-14.md`. Kept as written for the record.

# Handoff: OPS-12 — real persistence

Branch `refactor/OPS-12-real-persistence`, off `dev`. Read this before
touching code.

**Update:** the blocker in section 2 is fixed and verified end-to-end against
the real Neon database and the real `greader` R2 bucket (พาย applied the
`tables.py` fix and ran the pending migration in this session — see the final
commits on this branch). Section 2 is kept below as the record of what the bug
was and why the fix looks the way it does; it is no longer an open item.

## 1. What shipped

| Commit | What |
|---|---|
| `bfa9979` | `config.py` centralizes every env read. `database/session.py` and `database/storage/` build the engine and R2 client lazily from `Settings`, not at import time. |
| `9829c46` | `repository.py` → `ports.py` rename in `topics`, `assignments`, `generation`. |
| `97bc275` | Assignments + new `core/uploads/` slice wired to `SQLAssignmentRepository` / `SQLKnowledgeDocumentRepository`. `AssignmentUpdate` (one schema, all-optional, served under `PUT`) split into `AssignmentReplace` (`PUT`) / `AssignmentPatch` (`PATCH`), matching how Topics already did it. Services now raise `*NotFoundError` instead of returning `bool`. `difficulty` is a `Difficulty` `StrEnum`. Contract tests moved to `tests/contracts/`, run against both the fake and the SQL adapter. Every in-memory adapter moved out of `src/` into `tests/fakes/`. |
| `bfb236f` | `core.topics` table + migration (`alembic/versions/d3b7c1e9a204_add_core_topics_table.py`). `Topic.id` UUID → int. `main.py` rewritten: every port defaults to its SQL/R2 adapter — no code path left where the running app serves process memory. |

State at handoff: `uv run pytest` → 114 passed, 39 skipped (db/R2 tests
skip with no credentials, by design). `uv run ruff check .` and
`uv run ruff format --check .` both clean.

## 2. The blocker — read this before doing anything else

`database/core/tables.py` fails at `sqlalchemy.orm.configure_mappers()`
the moment any row (`Assignment`, `Topic`, `KnowledgeDocument`, or
anything reachable from `User`) is instantiated against a real engine:

```
sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[User(users)],
expression "relationship('list[KnowledgeDocument]')" seems to be using a generic
class as the argument to relationship(); please state the generic argument using
an annotation, e.g. "documents: Mapped[list['KnowledgeDocument']] = relationship()"
```

**Root cause:** `tables.py` has `from __future__ import annotations` at
the top, which turns every annotation into a string. Nine
`Relationship(...)`-typed attributes use bare `list[X]` / `X | None`
instead of `Mapped[list["X"]]` / `Mapped[Optional["X"]]`, which
SQLAlchemy 2.0.52 (installed) cannot resolve under deferred annotations.

**Confirmed pre-existing** — reproduced against `dev`'s untouched
`tables.py` in isolation, before this branch touched the file. Not
introduced by OPS-12. It was latent because nothing before this branch
ever built a real repository adapter that instantiates these rows —
`/health/db` only runs raw `SELECT 1`, so it never hit the mapper.

**Impact:** blocks every real write through `core.assignments`,
`core.topics`, `core.knowledge_documents` — i.e. it blocks the entire
point of OPS-12, at the ORM level, not at the adapter level. The three
new `tests/db/` files this branch added exercise exactly this path and
have never run against a real database.

**This file is locked.** Per `AGENTS.md` / `docs/task-scope.md`, only
พาย may edit `database/core/tables.py`. `.github/CODEOWNERS` enforces
it at the PR level. Do not edit it without พาย's review.

### Exact fix

Add to the imports:

```python
from sqlalchemy.orm import Mapped
from typing import Optional
```

Then, in `src/greader/database/core/tables.py`:

| Line | Current | Change to |
|---|---|---|
| 101 | `documents: list[KnowledgeDocument] = Relationship(...)` | `documents: Mapped[list["KnowledgeDocument"]] = Relationship(...)` |
| 102-104 | `generation_requests: list[GenerationRequest] = Relationship(...)` | `generation_requests: Mapped[list["GenerationRequest"]] = Relationship(...)` |
| 135 | `uploader: User \| None = Relationship(...)` | `uploader: Mapped[Optional["User"]] = Relationship(...)` |
| 168 | `requester: User \| None = Relationship(...)` | `requester: Mapped[Optional["User"]] = Relationship(...)` |
| 169 | `artifacts: list[GenerationArtifact] = Relationship(...)` | `artifacts: Mapped[list["GenerationArtifact"]] = Relationship(...)` |
| 210 | `assignment: Assignment \| None = Relationship(...)` | `assignment: Mapped[Optional["Assignment"]] = Relationship(...)` |
| 250 | `artifact: GenerationArtifact \| None = Relationship(...)` | `artifact: Mapped[Optional["GenerationArtifact"]] = Relationship(...)` |
| 251-253 | `test_cases: list[TestCase] = Relationship(...)` | `test_cases: Mapped[list["TestCase"]] = Relationship(...)` |
| 283 | `assignment: Assignment \| None = Relationship(...)` | `assignment: Mapped[Optional["Assignment"]] = Relationship(...)` |

Plain (non-relationship) columns — `id: int | None = _pk()`,
`metadata_: dict = ...` — are unaffected. Only `Relationship(...)`-typed
attributes need this.

## 3. To-do, in order

1. **พาย applies (or approves) the fix above** to `tables.py`.
2. Sanity-check the fix: instantiate an `Assignment` row through
   `SQLAssignmentRepository.create()` against a real engine and confirm
   `configure_mappers()` no longer raises. Quick repro:
   ```bash
   uv run python -c "
   from greader.database.session import build_engine, build_session_factory
   from greader.database.core.assignment_repository import SQLAssignmentRepository
   from greader.core.assignments.models import Assignment, Difficulty
   from greader.config import get_settings
   repo = SQLAssignmentRepository(build_session_factory(build_engine(get_settings())))
   print(repo.create(Assignment(title='t', problem_statement='p', difficulty=Difficulty.EASY)))
   "
   ```
3. Run `tests/db/` against a throwaway Neon branch:
   ```bash
   POSTGRES_TEST_URL=<throwaway-branch-dsn> uv run pytest -m postgres
   ```
   Three new files exercise the fixed path:
   `tests/db/test_assignment_repository.py`,
   `tests/db/test_topic_repository.py`,
   `tests/db/test_knowledge_document_repository.py`.
4. **Resume Stage 4** (not started):
   - Sync `docs/task-scope.md` / `AGENTS.md` / `README.md`:
     `repository.py` → `ports.py` terminology, fakes now live in
     `tests/fakes/` not `src/`, "8 tables" → 9 (added `core.topics`).
   - `POST /api/v1/generations` still proxies `StubGenerationClient`
     without persisting a `core.generation_requests` /
     `core.generation_artifacts` row. CORE-07's "create an assignment
     from an approved artifact" flow needs this row to exist first.
5. Push the branch and open the PR **only after** `tests/db/` passes
   for real, not before — Definition of Done requires the PR to quote
   CI for its own head commit, and a pre-existing local pass is not
   evidence the new code works if it was never exercised against
   Postgres.

## 4. Not included here

The full original code-review findings (naming issues, doc drift,
`dd`/`message.txt` stray root files) are in this branch's commit
messages — each commit explains the "why" for what it touched. This
doc only covers the blocker and what's left; it isn't a re-statement of
the full review.
