# Database — Core Schema on Neon PostgreSQL

Owner: Database owner

Structured data lives on **Neon PostgreSQL**, versioned with **Alembic** on
top of **SQLModel** table definitions. Files and PDFs live on **Cloudflare
R2** (`storage.py`) — the database only stores object keys and metadata.

Status: schema is live and applied to the real Neon database (`alembic
current` == `alembic heads` after the steps below). This replaces the old
in-memory placeholder note — Core services still access data only through
the repository interface, never through SQLModel/SQLAlchemy directly (rule
5 below).

## Layout

```text
src/greader/database/
├── __init__.py       # registers core_tables + rag_tables on SQLModel.metadata
├── README.md          # this file
├── session.py          # engine + get_session() dependency, reads DATABASE_URL
├── health.py            # /health/db check: SELECT 1 + confirms core/rag schemas exist
├── storage.py             # R2 (S3-compatible) client, /health/r2 check
├── core/
│   ├── __init__.py
│   └── tables.py            # SQLModel tables for schema `core`
└── rag/
    ├── __init__.py
    └── tables.py             # SQLModel tables for schema `rag` (pgvector)

alembic/
├── README
├── env.py             # loads DATABASE_URL, target_metadata, include_schemas=True
├── script.py.mako
└── versions/
    ├── bb6a005fe34c_core_and_rag_schema.py     # initial core/rag schema + extensions
    └── 93cd0a90c897_sync_core_schema_with_current_models.py

alembic.ini
```

Rules this module enforces:

1. Database owner designs the one Core schema (`core/tables.py`, `rag/tables.py`).
2. Migrations come after the schema is agreed (`alembic revision --autogenerate`).
3. Structured data → Neon PostgreSQL. Files/PDFs → Cloudflare R2 (`storage.py`), database keeps only the object key + metadata.
4. The database adapter sits behind the Core module's repository interface — Core service code stays unchanged.
5. Core service (`src/greader/core/**`) must never import SQLModel/SQLAlchemy/boto3 directly. Only `database/**` is allowed to.

## Environment

Set in `.env` (never commit it — see `.env.example`):

```bash
# Must include the +psycopg driver tag — project uses psycopg v3, not psycopg2.
DATABASE_URL=postgresql+psycopg://user:pass@host/db?sslmode=require
```

`alembic/env.py` reads `DATABASE_URL_UNPOOLED` from the process environment
and overrides `alembic.ini`'s placeholder URL with it (changed from
`DATABASE_URL` — Alembic runs DDL over a direct connection, not the pooled
one). The app (`session.py`) still reads `DATABASE_URL`. Both `env.py` and
`session.py` call `load_dotenv()` on import, so a local `.env` loads
automatically — no manual `export` needed before `uv run alembic ...`.

## Prisma-equivalent workflow

If you know Prisma, this is the same loop with different command names:

| Prisma | This project | What it does |
|---|---|---|
| edit `schema.prisma` | edit `core/tables.py` or `rag/tables.py` | change the model |
| `prisma migrate dev --name X` | `uv run alembic revision --autogenerate -m "X"` | diff models vs DB, write a migration file |
| (dev auto-applies) | `uv run alembic upgrade head` | apply pending migrations to the DB |
| `prisma migrate deploy` | `uv run alembic upgrade head` (in CI/prod) | apply migrations, no autogenerate |
| `prisma migrate reset` | `uv run alembic downgrade base` then `upgrade head` | drop and rebuild from migrations |
| `prisma studio` / inspect | `uv run alembic current`, `uv run alembic check` | see applied revision / detect drift |
| `prisma migrate status` | `uv run alembic history`, `uv run alembic current` | list revisions, show head |

There is no `db push`/no-migration-file mode here — every schema change goes
through a committed migration file, always.

### Add a new table or column

1. Edit `src/greader/database/core/tables.py` (or `rag/tables.py`) — add the
   `SQLModel` class or field. New table modules must be imported in
   `src/greader/database/__init__.py` so `SQLModel.metadata` sees them.
2. Generate the migration:
   ```bash
   uv run alembic revision --autogenerate -m "add <thing>"
   ```
3. **Read the generated file in `alembic/versions/`.** Autogenerate misses:
   default column renames (reads as drop+add), table/column renames, and
   some check-constraint edits. Adjust `upgrade()`/`downgrade()` by hand
   when needed.
4. Apply it:
   ```bash
   uv run alembic upgrade head
   ```
5. Confirm no drift remains:
   ```bash
   uv run alembic check   # "No new upgrade operations detected."
   ```

### Roll back

```bash
uv run alembic downgrade -1     # one revision back
uv run alembic downgrade <rev>  # to a specific revision
uv run alembic downgrade base   # all the way to empty
```

### Everyday commands

```bash
uv run alembic current            # current DB revision
uv run alembic heads              # latest revision(s) in versions/
uv run alembic history --verbose  # full revision graph
uv run alembic check              # detect model/DB drift without writing a file
uv run alembic upgrade head       # apply all pending migrations
uv run alembic downgrade -1       # roll back one migration
```

### Current schema

- `core.users`, `core.knowledge_documents`, `core.generation_requests`,
  `core.generation_artifacts`, `core.assignments`, `core.test_cases`
- `rag.knowledge_sources`, `rag.knowledge_chunks` (pgvector `embedding` column)

---

## คำแนะนำภาษาไทย

เจ้าของงาน: Database owner

ข้อมูลโครงสร้าง (structured data) เก็บบน **Neon PostgreSQL** ควบคุมเวอร์ชัน
schema ด้วย **Alembic** โดยอ่าน table definition จาก **SQLModel** ส่วนไฟล์
และ PDF เก็บบน **Cloudflare R2** (`storage.py`) — database เก็บแค่ object
key กับ metadata เท่านั้น

สถานะปัจจุบัน: schema ถูก apply เข้า Neon จริงแล้ว (`alembic current` ตรงกับ
`alembic heads`) Core service ยังต้องเข้าถึงข้อมูลผ่าน repository interface
เท่านั้น ห้าม import SQLModel/SQLAlchemy ตรงๆ (กฎข้อ 5 ด้านล่าง)

### กฎที่โมดูลนี้บังคับใช้

1. Database owner ออกแบบ Core schema ชุดเดียว (`core/tables.py`, `rag/tables.py`)
2. Migration มาหลังจาก schema ตกลงกันแล้วเท่านั้น (`alembic revision --autogenerate`)
3. Structured data → Neon PostgreSQL, ไฟล์/PDF → Cloudflare R2 (`storage.py`) database เก็บเพียง object key + metadata
4. Database adapter อยู่หลัง repository interface ของ Core module — Core service ไม่ต้องแก้
5. Core service (`src/greader/core/**`) ห้าม import SQLModel/SQLAlchemy/boto3 ตรงๆ เด็ดขาด อนุญาตเฉพาะใน `database/**`

### ตั้งค่า environment

ตั้งใน `.env` (ห้าม commit — ดู `.env.example`):

```bash
# ต้องมี driver tag +psycopg เสมอ (โปรเจกต์ใช้ psycopg v3 ไม่ใช่ psycopg2)
DATABASE_URL=postgresql+psycopg://user:pass@host/db?sslmode=require
```

### เทียบ workflow กับ Prisma

ถ้าคุ้นเคย Prisma อยู่แล้ว นี่คือ loop เดียวกัน แค่คนละชื่อคำสั่ง:

| Prisma | โปรเจกต์นี้ | ทำอะไร |
|---|---|---|
| แก้ `schema.prisma` | แก้ `core/tables.py` หรือ `rag/tables.py` | เปลี่ยน model |
| `prisma migrate dev --name X` | `uv run alembic revision --autogenerate -m "X"` | diff model กับ DB แล้วสร้างไฟล์ migration |
| (dev apply ให้อัตโนมัติ) | `uv run alembic upgrade head` | apply migration ที่ค้างอยู่เข้า DB |
| `prisma migrate deploy` | `uv run alembic upgrade head` (บน CI/prod) | apply migration ไม่มี autogenerate |
| `prisma migrate reset` | `uv run alembic downgrade base` แล้ว `upgrade head` | ล้างแล้วสร้างใหม่จาก migration ทั้งหมด |
| `prisma studio` / ดูสถานะ | `uv run alembic current`, `uv run alembic check` | ดู revision ปัจจุบัน / เช็ค drift |
| `prisma migrate status` | `uv run alembic history`, `uv run alembic current` | ดูรายการ revision / head ปัจจุบัน |

ที่นี่ไม่มีโหมด `db push` (schema change แบบไม่มีไฟล์ migration) — ทุกการแก้
schema ต้องผ่านไฟล์ migration ที่ commit เสมอ

### เพิ่มตารางหรือคอลัมน์ใหม่

1. แก้ `src/greader/database/core/tables.py` (หรือ `rag/tables.py`) — เพิ่ม
   class `SQLModel` หรือ field ใหม่ ถ้าเป็นไฟล์ตารางใหม่ ต้อง import ใน
   `src/greader/database/__init__.py` ด้วย ไม่งั้น `SQLModel.metadata` จะมองไม่เห็น
2. สร้างไฟล์ migration:
   ```bash
   uv run alembic revision --autogenerate -m "add <thing>"
   ```
3. **อ่านไฟล์ที่ generate ใน `alembic/versions/` ทุกครั้ง** Autogenerate จับ
   ไม่ได้บางเคส: rename column (จะเห็นเป็น drop+add), rename table, และ
   check constraint บางแบบ ต้องแก้ `upgrade()`/`downgrade()` เองถ้าจำเป็น
4. Apply เข้า DB:
   ```bash
   uv run alembic upgrade head
   ```
5. เช็คว่าไม่มี drift เหลือ:
   ```bash
   uv run alembic check   # ต้องได้ "No new upgrade operations detected."
   ```

### ย้าย schema กลับ (rollback)

```bash
uv run alembic downgrade -1     # ถอยกลับ 1 revision
uv run alembic downgrade <rev>  # ถอยไปที่ revision ที่ระบุ
uv run alembic downgrade base   # ถอยกลับจนว่างเปล่า
```

### คำสั่งที่ใช้บ่อย

```bash
uv run alembic current            # revision ปัจจุบันของ DB
uv run alembic heads              # revision ล่าสุดใน versions/
uv run alembic history --verbose  # กราฟ revision ทั้งหมด
uv run alembic check              # เช็ค drift ระหว่าง model กับ DB โดยไม่สร้างไฟล์
uv run alembic upgrade head       # apply migration ที่ค้างทั้งหมด
uv run alembic downgrade -1       # ถอยกลับ 1 migration
```

### Schema ปัจจุบัน

- `core.users`, `core.knowledge_documents`, `core.generation_requests`,
  `core.generation_artifacts`, `core.assignments`, `core.test_cases`
- `rag.knowledge_sources`, `rag.knowledge_chunks` (มีคอลัมน์ `embedding` แบบ pgvector)
