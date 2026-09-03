# GReader

**Language:** English | [ภาษาไทย](README.th.md)

GReader is a FastAPI application that helps instructors prepare programming
assignments, test cases, and related learning materials. It is organized as a
modular monolith so each team can develop its area without tightly coupling it
to the rest of the application.

The project is currently under development. The Topics API is the reference
feature, while the Assignment and AI modules are still being built. Topic data
is stored in memory and is cleared whenever the server restarts.

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/03376124-SDD-2-1-69-SEC-1/PyJudge.git
cd PyJudge
```

If `git` is not recognized, install it using the instructions in the next
section, then run the clone command again.

### 2. Check the Required Tools

The project requires Git, `uv`, and Python 3.12 or newer.

#### macOS

Open Terminal and run:

```bash
git --version
uv --version
python3 --version
```

Install any missing tools:

```bash
# Git (Apple Command Line Tools)
xcode-select --install

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Python 3.12 managed by uv
uv python install 3.12
```

#### Windows

Open PowerShell and run:

```powershell
git --version
uv --version
py --version
```

Install any missing tools with WinGet:

```powershell
# Git
winget install --id Git.Git -e --source winget

# uv
winget install --id astral-sh.uv -e

# Python 3.12 managed by uv
uv python install 3.12
```

Restart the terminal after installing a tool, then run the version checks
again. Alternative installers are available from the official
[Git](https://git-scm.com/install/) and
[`uv`](https://docs.astral.sh/uv/getting-started/installation/) pages.

### 3. Install the Project Dependencies

Run this command from the project directory:

```bash
uv sync
```

`uv` creates a local virtual environment and installs the locked dependencies.
You do not need to activate the environment when using `uv run`.

### 4. Configure the Environment

Create a local `.env` file from the template.

On macOS:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` and provide the credentials supplied by your team. The application
currently needs a Neon PostgreSQL connection in `DATABASE_URL` and these
Cloudflare R2 values:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@host/database?sslmode=require
R2_ENDPOINT_URL=
R2_BUCKET_NAME=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
```

Set `GEMINI_API_KEY` when working on Gemini integration. Never commit `.env` or
place real credentials in `.env.example`.

### 5. Apply Database Migrations

```bash
uv run --env-file .env alembic upgrade head
```

### 6. Start the Development Server

```bash
uv run --env-file .env uvicorn greader.main:app --reload
```

Open <http://127.0.0.1:8000> in your browser. Stop the server with `Ctrl+C`.

## Useful URLs

| URL | Description |
|---|---|
| <http://127.0.0.1:8000/> | Home page |
| <http://127.0.0.1:8000/docs> | Interactive API documentation |
| <http://127.0.0.1:8000/api/v1/topics> | Topics API |
| <http://127.0.0.1:8000/health> | Application health |
| <http://127.0.0.1:8000/health/db> | Neon PostgreSQL health |
| <http://127.0.0.1:8000/health/r2> | Cloudflare R2 health |

## Development Commands

Run the test suite:

```bash
uv run --env-file .env pytest
```

Check linting and formatting:

```bash
uv run ruff check .
uv run ruff format --check .
```

Create a migration after changing database models:

```bash
uv run --env-file .env alembic revision --autogenerate -m "describe the change"
```

## Project Structure

```text
src/greader/
├── main.py             # FastAPI application composition
├── core/
│   ├── topics/         # Reference Topics CRUD feature
│   └── assignments/    # Assignment module
├── ai/                 # AI integration area
├── database/           # Neon, SQLModel, Alembic, and R2 adapters
└── web/                # Jinja templates and static assets

alembic/                # Database migrations
tests/                  # Unit, integration, and architecture tests
```

## Data Model Reference

Reference documentation for the project's database layer — pairs with
`HANDOFF-data-modeling.md` (that file holds the *reasoning* behind decisions;
this one holds the *current state* of the code).

### 1. Actual stack

**One ORM, not two** — a common misconception.

```text
┌─────────────────────────────────────────┐
│  SQLModel                               │  ← where we write models
│  (Field, Relationship, SQLModel)        │
├─────────────────────────────────────────┤
│  SQLAlchemy Core + ORM                  │  ← what actually talks to the DB
│  (Column, BigInteger, ForeignKey, ...)  │
├─────────────────────────────────────────┤
│  psycopg v3                             │  ← driver
├─────────────────────────────────────────┤
│  PostgreSQL (Neon) + pgvector extension │
└─────────────────────────────────────────┘
```

| Piece | What it is | Why it's needed |
|---|---|---|
| **SQLModel** | Thin layer wrapping SQLAlchemy + Pydantic | Shorter models, free validation |
| **SQLAlchemy** | The real ORM/Core | SQLModel doesn't wrap everything; missing pieces are called directly |
| **pgvector** | **Not an ORM** — extension + column type | Lets SQLAlchemy recognize the `VECTOR(768)` type |
| **psycopg v3** | Database driver | Sends the actual SQL to Postgres |

Why code imports from `sqlalchemy` directly:

```python
from sqlmodel import Field, Relationship, SQLModel       # top layer
from sqlalchemy import Column, BigInteger, ForeignKey    # what SQLModel doesn't wrap
from sqlalchemy.dialects.postgresql import JSONB         # Postgres-specific type
from pgvector.sqlalchemy import Vector                   # type from the extension
```

Not two ORMs mixed together — one stack, different layers.

**Consequence for `.env`:** since SQLAlchemy (not SQLModel) reads the
connection string, the driver must be `postgresql+psycopg://`, not the plain
`postgresql://` Neon copies by default — otherwise it looks for `psycopg2`
(the old driver), which isn't installed.

### 2. Folder structure

```text
src/greader/
├── core/                        ← Core Service (must not import an ORM)
│   ├── topics/                  ✅ reference slice
│   │   ├── models.py            dataclass(frozen=True, slots=True)
│   │   ├── repository.py        typing.Protocol + in-memory impl
│   │   ├── service.py           pure sync, receives repo via constructor
│   │   └── routes.py            sync def, pulls service from app.state
│   └── assignments/              🔒 teammate — still docstrings only
│       ├── models.py            plain dataclasses
│       ├── repository.py        Protocol interface
│       ├── service.py
│       └── routes.py
│
├── database/                    ← the only place allowed to import an ORM
│   ├── __init__.py              imports tables from both sides (matters for alembic)
│   ├── session.py               engine + get_session (sync)
│   ├── README.md
│   ├── core/
│   │   ├── __init__.py
│   │   ├── tables.py            ✅ SQLModel — schema `core`
│   │   └── assignment_repository.py   ⏳ adapter (waiting on teammate's Protocol)
│   └── rag/
│       ├── __init__.py
│       └── tables.py            ✅ SQLModel — schema `rag`
│
├── ai/                          ← AI/RAG Service (not started)
└── web/                         ← Jinja2 templates

alembic/                         ← at repo root, by convention
├── env.py                       target_metadata = SQLModel.metadata
│                                include_schemas=True
│                                uses DATABASE_URL_UNPOOLED
└── versions/
```

Hard rule — import direction:

```text
core/assignments/models.py      (dataclass)
core/assignments/repository.py  (Protocol)
            ↑ implemented by ↓
database/core/assignment_repository.py   ← adapter lives here, and only here
            ↓ uses ↓
database/core/tables.py         (SQLModel)
```

The adapter must live under `database/` because it needs both SQLModel and the
dataclass — this seam must never live on the `core/` side.

The alembic mistake that keeps happening: `--autogenerate` only sees table
classes that have **already been imported**. Dropping a file in place isn't
enough — it must be imported in `database/__init__.py`:

```python
from greader.database.core import tables as core_tables  # noqa: F401
from greader.database.rag import tables as rag_tables    # noqa: F401
```

Forget this and it won't error — it silently generates a migration missing
that table, and the next autogenerate run may issue `drop_table` on a table
that genuinely exists in the DB. **Always open and review the migration file
before running it.**

### 3. ERD

```mermaid
erDiagram
    direction TB

    %% ==================== schema: core ====================

    users {
        BIGSERIAL id PK
        TEXT email UK "indexed"
        TEXT display_name "nullable"
        TEXT role "CHECK: instructor | admin, default instructor"
        TIMESTAMPTZ created_at "default now()"
        TIMESTAMPTZ updated_at "default now(), onupdate"
    }

    knowledge_documents {
        BIGSERIAL id PK
        TEXT r2_object_key UK "natural key, cross-checked when mirroring"
        TEXT filename
        TEXT content_hash "sha256, prevents duplicate files"
        TEXT status "CHECK: uploaded | ingesting | ready | failed"
        JSONB metadata "topic, difficulty, course"
        BIGINT uploaded_by FK "nullable, ON DELETE SET NULL"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    generation_requests {
        BIGSERIAL id PK
        TEXT prompt
        JSONB filters "topic, difficulty — must match keys in metadata"
        TEXT status "CHECK: pending | generating | completed | failed"
        TEXT error_code "nullable"
        BIGINT requested_by FK "nullable, ON DELETE SET NULL"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    generation_artifacts {
        BIGSERIAL id PK
        BIGINT request_id FK "NOT NULL, ON DELETE CASCADE"
        JSONB draft "title, statement, test_cases — no default"
        JSONB citations "chunk_id, source_id, page, score, text_snapshot"
        TEXT model_provider "nullable"
        TEXT model_name "nullable, e.g. gemini-2.0-flash"
        TEXT review_status "CHECK: pending | applied | discarded"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    assignments {
        BIGSERIAL id PK
        BIGINT artifact_id FK,UK "nullable when hand-created, ON DELETE SET NULL"
        TEXT title
        TEXT problem_statement
        TEXT difficulty "CHECK: easy | medium | hard"
        JSONB metadata "topic, language, course"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    test_cases {
        BIGSERIAL id PK
        BIGINT assignment_id FK "NOT NULL, ON DELETE CASCADE"
        TEXT input_data
        TEXT expected_output
        BOOLEAN is_hidden "default false"
        INT order_index "default 0"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    %% ==================== schema: rag ====================

    knowledge_sources {
        BIGSERIAL id PK
        BIGINT core_document_id UK "logical link to core, no real FK"
        TEXT r2_object_key "duplicated from core on purpose, used to verify the link"
        TEXT content_hash
        TEXT status "CHECK: pending | processing | ready | failed"
        TEXT embedding_model "nullable"
        INT embedding_dim "nullable"
        JSONB metadata "GIN index — mirrored for filtering"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    knowledge_chunks {
        BIGSERIAL id PK
        BIGINT source_id FK "NOT NULL, ON DELETE CASCADE"
        INT chunk_index "order within source, indexed with source_id"
        INT page "nullable"
        TEXT text
        INT token_count "nullable, bounds context budget"
        TEXT content_hash "UNIQUE together with source_id"
        TEXT embedding_model "duplicated from source on purpose, prevents mixed-version vectors"
        JSONB metadata "question_no, content_type"
        VECTOR embedding "768 dims, nullable — HNSW index hand-written in migration"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    %% ==================== relationships ====================

    users ||--o{ knowledge_documents : "uploads"
    users ||--o{ generation_requests : "creates"
    generation_requests ||--o{ generation_artifacts : "produces"
    generation_artifacts ||--o| assignments : "applied to"
    assignments ||--o{ test_cases : "has"
    knowledge_sources ||--o{ knowledge_chunks : "split into"
    knowledge_documents ||..o| knowledge_sources : "cross-schema mirror (no real FK)"
```

### 4. What the ORM can't create — hand-write these in migrations

**4.1 Before the first migration:**

```sql
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE EXTENSION IF NOT EXISTS vector;
```

**4.2 HNSW index (the most important one)** — autogenerate does not create
this, write it by hand in `op.execute()`:

```sql
CREATE INDEX ON rag.knowledge_chunks
USING hnsw (embedding vector_cosine_ops);
```

Without it, every query is a sequential scan. Invisible at low row counts,
but slow immediately once chunks reach the tens of thousands.

**4.3 Cross-schema cleanup has no cascade.** Deleting
`core.knowledge_documents` does **not** cascade to `rag.knowledge_sources` +
`knowledge_chunks`, because there is no real FK between them. Cleanup must be
handled at the application level (Core calls `DELETE /v1/knowledge/{id}` on
the AI service) — otherwise orphaned chunks stay retrievable even after the
source file has been deleted.

### 5. Decisions already closed

| Topic | Decision | Effect on code |
|---|---|---|
| `assignments.artifact_id` UNIQUE | **Yes, keep it** | `unique=True` on the Column + `uselist=False` on the relationship |
| Alembic history | **Core and rag share one history** — not split into separate repos, single node | `database/__init__.py` must import tables from both sides |
| Teammate's DB | **Same database** | Requires an explicit migration agreement (see 5.1) |

**5.1 Sharing one database — what still needs agreeing.** Two teammates
sharing one database is fine for an MVP, but three cases will come up if they
aren't discussed beforehand:

1. **`alembic downgrade` affects the other person immediately.** The handoff
   already says the teammate doesn't touch migrations, so only one person runs
   downgrade — but they must announce it first, or the teammate's app breaks
   mid-session for no visible reason.
2. **Test data collides.** If the teammate writes CRUD and inserts/deletes
   test assignments, that data mixes with ours. Easiest fix: agree a
   convention (e.g. a title prefix for test data), or use a separate Neon
   branch just for running tests.
3. **If we decide to split later**, Neon's **branch** feature can copy the
   whole database in seconds (copy-on-write, no extra storage cost). If
   collisions become frequent, giving the teammate their own branch takes
   minutes — no need to decide now.

Since we've agreed on "single node, not split," this should be recorded as an
ADR after `0003-`, so future readers know it was a deliberate choice, not a
forgotten split.

### 6. Still open

| Topic | Status |
|---|---|
| `main.py` doesn't mount the assignment router yet | Need to agree who adds it |
| Real embedding model | `VECTOR(768)` is a one-way door — changing dimensions later means migrating the whole table |
| Protocol in `core/assignments/repository.py` | Waiting on the teammate to define it before the adapter can be written |

## Technology Stack

- Python 3.12+
- FastAPI and Uvicorn
- SQLModel, SQLAlchemy, and Alembic
- Neon PostgreSQL
- Cloudflare R2 with Boto3
- Jinja2
- Pytest and Ruff
- `uv` for Python and dependency management
