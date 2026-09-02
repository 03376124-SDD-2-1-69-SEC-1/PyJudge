# Database Placeholder

เจ้าของงาน: Database owner

ตอนนี้ระบบใช้ in-memory state เพื่อให้ทีมเห็น API flow โดยไม่ผูกกับ schema
จริง ข้อมูลจึงหายเมื่อ restart

เมื่อเริ่มงาน database:

1. ออกแบบและ init Core schema หนึ่งชุดก่อน
2. เพิ่ม database adapter หลัง repository interface ของ Core module
3. เก็บ structured data บน Neon PostgreSQL
4. เก็บไฟล์และ PDF บน Cloudflare R2; database เก็บเพียง object key และ metadata
5. อย่าให้ Core service import ORM หรือ storage client โดยตรง

ยังไม่กำหนด table, migration หรือ credential ใน repository นี้ เพราะเป็น
ขอบเขตของ Database owner

## Setup & Migration Workflow

Current layout:

```text
src/greader/database/
├── __init__.py
├── README.md
└── core/
    └── __init__.py

alembic/
├── README
├── env.py
├── script.py.mako
└── versions/

alembic.ini
```

- `src/greader/database/__init__.py`: marks database directory as a Python package.
- `src/greader/database/README.md`: documents database ownership and migration workflow.
- `src/greader/database/core/`: reserved package for Core database definitions.
- `src/greader/database/core/__init__.py`: marks Core database directory as a Python package.
- `alembic/`: Alembic migration environment.
- `alembic/README`: generated Alembic environment notes.
- `alembic/env.py`: generated Alembic migration runtime configuration.
- `alembic/script.py.mako`: generated template for migration revisions.
- `alembic/versions/`: stores generated migration revision files.
- `alembic.ini`: generated Alembic command and logging configuration.

Expected database implementation files `src/greader/database/session.py` and
`src/greader/database/core/tables.py` are not present in this checkout.

- `uv run alembic revision --autogenerate -m "<message>"`: generates a migration from metadata changes.
- `uv run alembic upgrade head`: applies all pending migrations.
- `uv run alembic downgrade -1`: rolls back one migration.
- `uv run alembic current`: shows current database revision.
- `uv run alembic history`: shows migration revision history.

target_metadata / multi-schema wiring in alembic/env.py is not done yet — this is a follow-up task.
