# GReader

**ภาษา:** [English](README.md) | ภาษาไทย

GReader คือแอปพลิเคชัน FastAPI ที่ช่วยผู้สอนเตรียมโจทย์เขียนโปรแกรม ชุดทดสอบ
และสื่อการเรียนที่เกี่ยวข้อง โปรเจกต์ใช้สถาปัตยกรรมแบบ modular monolith
เพื่อให้แต่ละทีมพัฒนาส่วนที่รับผิดชอบได้โดยไม่ผูกกับส่วนอื่นมากเกินไป

ขณะนี้โปรเจกต์ยังอยู่ระหว่างการพัฒนา Topics API เป็นฟีเจอร์อ้างอิง
ส่วนโมดูล Assignment และ AI ยังอยู่ระหว่างการพัฒนา ข้อมูล Topic
ถูกเก็บไว้ในหน่วยความจำและจะหายเมื่อรีสตาร์ตเซิร์ฟเวอร์

## เริ่มต้นใช้งาน

### 1. Clone Repository

```bash
git clone https://github.com/03376124-SDD-2-1-69-SEC-1/PyJudge.git
cd PyJudge
```

หากระบบไม่รู้จักคำสั่ง `git` ให้ติดตั้งตามหัวข้อถัดไป แล้วจึงรันคำสั่ง clone
อีกครั้ง

### 2. ตรวจสอบเครื่องมือที่จำเป็น

โปรเจกต์ต้องใช้ Git, `uv` และ Python 3.12 ขึ้นไป

#### macOS

เปิด Terminal แล้วรัน:

```bash
git --version
uv --version
python3 --version
```

ติดตั้งเครื่องมือที่ยังไม่มี:

```bash
# Git (Apple Command Line Tools)
xcode-select --install

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Python 3.12 ที่จัดการโดย uv
uv python install 3.12
```

#### Windows

เปิด PowerShell แล้วรัน:

```powershell
git --version
uv --version
py --version
```

ติดตั้งเครื่องมือที่ยังไม่มีด้วย WinGet:

```powershell
# Git
winget install --id Git.Git -e --source winget

# uv
winget install --id astral-sh.uv -e

# Python 3.12 ที่จัดการโดย uv
uv python install 3.12
```

หลังติดตั้งเครื่องมือให้เปิด Terminal หรือ PowerShell ใหม่ แล้วตรวจสอบเวอร์ชัน
อีกครั้ง สามารถดูวิธีติดตั้งทางเลือกได้จากหน้าอย่างเป็นทางการของ
[Git](https://git-scm.com/install/) และ
[`uv`](https://docs.astral.sh/uv/getting-started/installation/)

### 3. ติดตั้ง Dependencies

รันคำสั่งนี้ภายในไดเรกทอรีของโปรเจกต์:

```bash
uv sync
```

`uv` จะสร้าง virtual environment และติดตั้ง dependencies ตาม lockfile
โดยไม่จำเป็นต้อง activate environment เมื่อใช้คำสั่ง `uv run`

### 4. ตั้งค่า Environment

สร้างไฟล์ `.env` จากไฟล์ตัวอย่าง

บน macOS:

```bash
cp .env.example .env
```

บน Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

เปิดไฟล์ `.env` แล้วกรอก credentials ที่ได้รับจากทีม ปัจจุบันแอปต้องใช้
การเชื่อมต่อ Neon PostgreSQL ใน `DATABASE_URL` และค่า Cloudflare R2 ต่อไปนี้:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@host/database?sslmode=require
R2_ENDPOINT_URL=
R2_BUCKET_NAME=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
```

กำหนด `GEMINI_API_KEY` เมื่อต้องพัฒนา Gemini integration ห้าม commit ไฟล์
`.env` หรือใส่ credentials จริงลงใน `.env.example`

### 5. รัน Database Migrations

```bash
uv run --env-file .env alembic upgrade head
```

### 6. เริ่ม Development Server

```bash
uv run --env-file .env uvicorn greader.main:app --reload
```

เปิด <http://127.0.0.1:8000> ในเบราว์เซอร์ หยุดเซิร์ฟเวอร์ด้วย `Ctrl+C`

## URL ที่ใช้งานบ่อย

| URL | รายละเอียด |
|---|---|
| <http://127.0.0.1:8000/> | หน้าแรก |
| <http://127.0.0.1:8000/docs> | เอกสาร API แบบโต้ตอบ |
| <http://127.0.0.1:8000/api/v1/topics> | Topics API |
| <http://127.0.0.1:8000/health> | สถานะแอปพลิเคชัน |
| <http://127.0.0.1:8000/health/db> | สถานะ Neon PostgreSQL |
| <http://127.0.0.1:8000/health/r2> | สถานะ Cloudflare R2 |

## คำสั่งสำหรับพัฒนา

รันชุดทดสอบ:

```bash
uv run --env-file .env pytest
```

ตรวจสอบ lint และรูปแบบโค้ด:

```bash
uv run ruff check .
uv run ruff format --check .
```

สร้าง migration หลังแก้ไข database models:

```bash
uv run --env-file .env alembic revision --autogenerate -m "describe the change"
```

## โครงสร้างโปรเจกต์

```text
sgreader/
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile
│
├── docs/
│
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
    └── unit/     # Unit, integration และ architecture tests
```

## เอกสารอ้างอิงโครงสร้างข้อมูล

เอกสารอ้างอิงโครงสร้าง database layer ของโปรเจกต์ — ใช้คู่กับ
`HANDOFF-data-modeling.md` (ไฟล์นั้นเก็บ *เหตุผล* ที่ตัดสินใจ ไฟล์นี้เก็บ
*สถานะปัจจุบัน* ของโค้ด)

### 1. Stack ที่ใช้จริง

**ใช้ ORM ตัวเดียว ไม่ใช่สองตัว** — เป็นความเข้าใจผิดที่เจอบ่อย

```text
┌─────────────────────────────────────────┐
│  SQLModel                               │  ← ที่เราเขียน model
│  (Field, Relationship, SQLModel)        │
├─────────────────────────────────────────┤
│  SQLAlchemy Core + ORM                  │  ← ตัวจริงที่คุยกับ DB
│  (Column, BigInteger, ForeignKey, ...)  │
├─────────────────────────────────────────┤
│  psycopg v3                             │  ← driver
├─────────────────────────────────────────┤
│  PostgreSQL (Neon) + pgvector extension │
└─────────────────────────────────────────┘
```

| ตัว | คืออะไร | ทำไมต้องมี |
|---|---|---|
| **SQLModel** | ชั้นบางๆ ที่ครอบ SQLAlchemy + Pydantic | เขียน model สั้นลง ได้ validation ฟรี |
| **SQLAlchemy** | ORM/Core ตัวจริง | SQLModel ไม่ได้ห่อทุกอย่าง ของที่ขาดต้องเรียกตรง |
| **pgvector** | **ไม่ใช่ ORM** — extension + column type | ให้ SQLAlchemy รู้จักชนิด `VECTOR(768)` |
| **psycopg v3** | database driver | ตัวส่ง SQL จริงไป Postgres |

ทำไมโค้ดถึง import จาก sqlalchemy ตรงๆ:

```python
from sqlmodel import Field, Relationship, SQLModel       # ชั้นบน
from sqlalchemy import Column, BigInteger, ForeignKey    # ของที่ SQLModel ไม่ได้ห่อ
from sqlalchemy.dialects.postgresql import JSONB         # ชนิดเฉพาะ Postgres
from pgvector.sqlalchemy import Vector                   # ชนิดจาก extension
```

ไม่ได้แปลว่าใช้ ORM ปนกัน — เป็น stack เดียวกันคนละชั้นเท่านั้น

**ผลที่ตามมาใน `.env`:** เพราะตัวที่อ่าน connection string คือ SQLAlchemy
(ไม่ใช่ SQLModel) จึงต้องระบุ driver เป็น `postgresql+psycopg://`
ไม่ใช่ `postgresql://` ที่ Neon ก็อปมาให้ — ไม่งั้นมันจะไปหา `psycopg2`
(ตัวเก่า) ที่ไม่ได้ติดตั้งไว้

### 2. โครงสร้างโฟลเดอร์

```text
src/greader/
├── core/                        ← Core Service (ห้าม import ORM)
│   ├── topics/                  ✅ reference slice
│   │   ├── models.py            dataclass(frozen=True, slots=True)
│   │   ├── repository.py        typing.Protocol + InMemory impl
│   │   ├── service.py           sync ล้วน รับ repo ผ่าน constructor
│   │   └── routes.py            sync def, ดึง service จาก app.state
│   └── assignments/             🔒 teammate — ยังเป็น docstring
│       ├── models.py            dataclass ล้วน
│       ├── repository.py        Protocol interface
│       ├── service.py
│       └── routes.py
│
├── database/                    ← ที่เดียวที่ import ORM ได้
│   ├── __init__.py              import tables ทั้ง 2 ฝั่ง (สำคัญกับ alembic)
│   ├── session.py               engine + get_session (sync)
│   ├── README.md
│   ├── core/
│   │   ├── __init__.py
│   │   ├── tables.py            ✅ SQLModel — schema `core`
│   │   └── assignment_repository.py   ⏳ adapter (รอ Protocol จาก teammate)
│   └── rag/
│       ├── __init__.py
│       └── tables.py            ✅ SQLModel — schema `rag`
│
├── ai/                          ← AI/RAG Service (ยังไม่เริ่ม)
└── web/                         ← Jinja2 templates

alembic/                         ← root ตาม convention
├── env.py                       target_metadata = SQLModel.metadata
│                                include_schemas=True
│                                ใช้ DATABASE_URL_UNPOOLED
└── versions/
```

กฎเหล็ก: ทิศทางการ import

```text
core/assignments/models.py      (dataclass)
core/assignments/repository.py  (Protocol)
            ↑ implement โดย ↓
database/core/assignment_repository.py   ← adapter อยู่ตรงนี้เท่านั้น
            ↓ ใช้ ↓
database/core/tables.py         (SQLModel)
```

Adapter ต้องอยู่ฝั่ง `database/` เพราะมันต้อง import ทั้ง SQLModel และ dataclass
— จุดเชื่อมนี้ห้ามอยู่ฝั่ง `core/`

เรื่อง alembic ที่พลาดกันบ่อย: `--autogenerate` เห็นเฉพาะ table class ที่
**ถูก import แล้ว** เท่านั้น วางไฟล์ไว้เฉยๆ ไม่พอ ต้อง import ใน
`database/__init__.py`:

```python
from greader.database.core import tables as core_tables  # noqa: F401
from greader.database.rag import tables as rag_tables    # noqa: F401
```

ถ้าลืม มันจะไม่ error — แต่จะ generate migration ที่ขาดตารางไปเงียบๆ
และรอบถัดไปอาจสั่ง `drop_table` ตารางที่มีอยู่จริงใน DB **เปิดไฟล์ migration
ตรวจทุกครั้งก่อนรัน**

### 3. ERD

```mermaid
erDiagram
    direction TB

    %% ==================== schema: core ====================

    users {
        BIGSERIAL id PK
        TEXT email UK "index"
        TEXT display_name "nullable"
        TEXT role "CHECK: instructor | admin, default instructor"
        TIMESTAMPTZ created_at "default now()"
        TIMESTAMPTZ updated_at "default now(), onupdate"
    }

    knowledge_documents {
        BIGSERIAL id PK
        TEXT r2_object_key UK "natural key ใช้ cross-check ตอน mirror"
        TEXT filename
        TEXT content_hash "sha256 กันไฟล์ซ้ำ"
        TEXT status "CHECK: uploaded | ingesting | ready | failed"
        JSONB metadata "topic, difficulty, course"
        BIGINT uploaded_by FK "nullable, ON DELETE SET NULL"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    generation_requests {
        BIGSERIAL id PK
        TEXT prompt
        JSONB filters "topic, difficulty — ต้อง match key ใน metadata"
        TEXT status "CHECK: pending | generating | completed | failed"
        TEXT error_code "nullable"
        BIGINT requested_by FK "nullable, ON DELETE SET NULL"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    generation_artifacts {
        BIGSERIAL id PK
        BIGINT request_id FK "NOT NULL, ON DELETE CASCADE"
        JSONB draft "title, statement, test_cases — ไม่มี default"
        JSONB citations "chunk_id, source_id, page, score, text_snapshot"
        TEXT model_provider "nullable"
        TEXT model_name "nullable, เช่น gemini-2.0-flash"
        TEXT review_status "CHECK: pending | applied | discarded"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    assignments {
        BIGSERIAL id PK
        BIGINT artifact_id FK,UK "nullable ถ้าสร้างมือ, ON DELETE SET NULL"
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
        BIGINT core_document_id UK "logical link ไป core ไม่มี FK จริง"
        TEXT r2_object_key "ซ้ำกับ core ตั้งใจ ใช้ verify link"
        TEXT content_hash
        TEXT status "CHECK: pending | processing | ready | failed"
        TEXT embedding_model "nullable"
        INT embedding_dim "nullable"
        JSONB metadata "GIN index — mirror มาเพื่อ filter"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    knowledge_chunks {
        BIGSERIAL id PK
        BIGINT source_id FK "NOT NULL, ON DELETE CASCADE"
        INT chunk_index "ลำดับใน source, index คู่กับ source_id"
        INT page "nullable"
        TEXT text
        INT token_count "nullable, คุม context budget"
        TEXT content_hash "UNIQUE คู่กับ source_id"
        TEXT embedding_model "ซ้ำจาก source ตั้งใจ กัน vector ปนรุ่น"
        JSONB metadata "question_no, content_type"
        VECTOR embedding "768 มิติ, nullable — HNSW เขียนมือใน migration"
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
    knowledge_documents ||..o| knowledge_sources : "mirror ข้ามschema (ไม่มี FK จริง)"
```

### 4. สิ่งที่ ORM สร้างให้ไม่ได้ — ต้องเขียนมือใน migration

**4.1 ก่อน migration แรก:**

```sql
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE EXTENSION IF NOT EXISTS vector;
```

**4.2 HNSW index (สำคัญที่สุด)** — autogenerate ไม่สร้างให้
ต้องเขียนเองใน `op.execute()`:

```sql
CREATE INDEX ON rag.knowledge_chunks
USING hnsw (embedding vector_cosine_ops);
```

ไม่มี → sequential scan ทั้งตาราง ตอนข้อมูลน้อยไม่รู้สึก
แต่หลักหมื่น chunk ขึ้นไปจะช้าทันที

**4.3 Cross-schema cleanup ไม่มี cascade.** ลบ `core.knowledge_documents`
แล้ว `rag.knowledge_sources` + `knowledge_chunks` **ไม่หายตาม**
เพราะไม่มี FK จริง ต้องเขียน cleanup ระดับ application (Core ยิง
`DELETE /v1/knowledge/{id}` ไป AI service) ไม่งั้นจะมี orphan chunk
ที่ยัง retrieve เจอ ทั้งที่ไฟล์ต้นฉบับถูกลบแล้ว

### 5. Decision ที่ปิดแล้ว

| เรื่อง | สรุป | ผลกับโค้ด |
|---|---|---|
| `assignments.artifact_id` UNIQUE | **ใส่** | `unique=True` บน Column + `uselist=False` บน relationship |
| Alembic history | **รวม core+rag ไว้ด้วยกัน** ไม่แยก repo, single node | `database/__init__.py` ต้อง import tables ทั้ง 2 ฝั่ง |
| DB ของ teammate | **ใช้ตัวเดียวกัน** | ต้องมีข้อตกลงเรื่อง migration (ดู 5.1) |

**5.1 ใช้ DB ตัวเดียวกัน — สิ่งที่ต้องตกลงเพิ่ม.** ทีม 2 คนใช้ database
เดียวกันไม่ผิดสำหรับ MVP แต่มี 3 เคสที่จะเจอแน่ๆ ถ้าไม่คุยกันก่อน:

1. **`alembic downgrade` กระทบอีกคนทันที** — handoff ระบุว่า teammate
   ไม่แตะ migration อยู่แล้ว ดังนั้นคนรัน downgrade จะมีแค่เราคนเดียว —
   แต่ต้องบอกก่อนรัน ไม่งั้นแอปฝั่ง teammate จะพังกลางคันโดยเขาไม่รู้สาเหตุ
2. **Test data ปนกัน** — ถ้า teammate เขียน CRUD แล้วลอง insert/delete
   assignment ข้อมูลจะปนกับของเรา ทางแก้ง่ายสุดคือตกลง convention เช่น
   ใส่ prefix ในชื่อ title ตอนเทส หรือใช้ Neon branch แยกเฉพาะตอนรัน test
3. **ถ้าเปลี่ยนใจอยากแยกทีหลัง** — Neon มีฟีเจอร์ **branch** ที่ copy
   database ทั้งก้อนได้ในไม่กี่วินาที (copy-on-write ไม่เปลืองที่)
   ถ้าวันไหนเริ่มชนกันบ่อย แยก branch ให้ teammate ใช้เวลาไม่กี่นาที
   ไม่ต้องตัดสินใจตอนนี้

เนื่องจากตกลงว่า "ไม่แยก repo, single node" แล้ว ควรบันทึกเป็น ADR
ต่อจาก `0003-` ไว้ด้วย เพื่อให้คนที่มาอ่านทีหลังรู้ว่าเป็นการเลือกที่ตั้งใจ
ไม่ใช่ลืมแยก

### 6. ที่ยังเปิดอยู่

| เรื่อง | สถานะ |
|---|---|
| `main.py` ยังไม่ mount assignment router | ต้องตกลงว่าใครใส่ |
| Embedding model ตัวจริง | `VECTOR(768)` เป็น one-way door เปลี่ยนมิติทีหลัง = migrate ทั้งตาราง |
| Protocol ใน `core/assignments/repository.py` | รอ teammate กำหนดก่อน ถึงจะเขียน adapter ได้ |

## เทคโนโลยีที่ใช้

- Python 3.12+
- FastAPI และ Uvicorn
- SQLModel, SQLAlchemy และ Alembic
- Neon PostgreSQL
- Cloudflare R2 และ Boto3
- Jinja2
- Pytest และ Ruff
- `uv` สำหรับจัดการ Python และ dependencies
