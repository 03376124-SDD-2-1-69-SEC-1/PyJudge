# GReader — Team Scaffold

GReader เป็นโครงตั้งต้นสำหรับงานกลุ่ม พัฒนาแบบ modular monolith ด้วย FastAPI
และ Jinja2

สถานะปัจจุบัน:

- core/topics เป็น CRUD API ตัวอย่างที่ใช้งานได้จริง
- core/assignments เป็น placeholder สำหรับทีม Assignment
- ai เป็น placeholder สำหรับทีม AI
- persistence เป็น placeholder สำหรับ Database owner
- หน้า / เป็น layout ตัวอย่างที่ทีม design แก้ครั้งเดียวและ page อื่นจะ inherit
  layout เดียวกัน

## โครงสร้าง

~~~text
src/greader/
├── main.py                 # composition root
├── core/
│   ├── topics/             # CRUD reference API
│   └── assignments/        # teammate-owned placeholder
├── ai/                     # teammate-owned placeholder
├── persistence/            # database-owner placeholder
└── web/
    ├── templates/          # base.html เป็น global layout
    └── static/css/         # Tailwind source + compiled CSS
~~~

## เริ่มใช้งาน

ต้องมี Python 3.12+ และ uv

~~~bash
uv sync
uv run uvicorn greader.main:app --reload
~~~

เปิด:

- หน้า layout: http://127.0.0.1:8000/
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## Topics API Reference

core/topics เป็นตัวอย่างให้ทีม backend ดู flow ที่ควรใช้:

~~~text
HTTP route → service → repository interface → in-memory adapter
~~~

| Method | Path | ความหมาย |
|---|---|---|
| POST | /api/v1/topics | สร้าง Topic |
| GET | /api/v1/topics | ดู Topics ทั้งหมด |
| GET | /api/v1/topics/{id} | ดู Topic เดียว |
| PUT | /api/v1/topics/{id} | แก้ Topic |
| DELETE | /api/v1/topics/{id} | ลบ Topic |

ทดลอง endpoint เหล่านี้ได้จาก Swagger โดยไม่ต้องมีฐานข้อมูล ข้อมูลเป็น
in-memory จึงหายเมื่อ restart server

## งานของแต่ละทีม

| งาน | เริ่มที่ |
|---|---|
| Assignment และ Test Case | src/greader/core/assignments/README.md |
| AI | src/greader/ai/README.md |
| Database / storage | src/greader/persistence/README.md |
| Design system / layout | src/greader/web/templates/base.html |

อ่าน AGENTS.md, CONTEXT.md, ADR และ plan.md ก่อนเริ่มงาน

## Database และ File Storage ในอนาคต

ล็อกแนวทางเป็น:

~~~text
FastAPI → Neon PostgreSQL  (structured data)
FastAPI → Cloudflare R2    (PDF / uploaded objects)
~~~

Neon เก็บข้อมูล relational ส่วน R2 เก็บไฟล์จริง โดย database เก็บเพียง object
key และ metadata. ตอนนี้ยังไม่มี schema, migration หรือ database adapter เพราะ
Database owner จะออกแบบและ init เอง

## Tailwind และข้อห้าม JavaScript

Template ของทีมไม่มี script element, javascript URL หรือ inline event handler.
FastAPI /docs ใช้ JavaScript ของ framework ได้ เพราะเป็น developer tooling
ที่สร้างโดย FastAPI ไม่ใช่ feature template ของทีม

แก้ Tailwind source ที่:

~~~text
src/greader/web/static/css/input.css
~~~

จากนั้น build ด้วย Tailwind standalone CLI ที่ทีมติดตั้งไว้:

~~~bash
tailwindcss -i src/greader/web/static/css/input.css -o src/greader/web/static/css/app.css --minify
~~~

ห้ามใช้ Node/npm และห้ามโหลด Tailwind runtime ใน browser

## Test และตรวจคุณภาพ

~~~bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
~~~

Tests ครอบคลุม Topics API, in-memory seam, layout และ architecture guard ที่กัน
JavaScript ใน template และกัน Core import AI
