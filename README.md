# GReader

GReader เป็นโครงตั้งต้นสำหรับระบบที่ช่วย Instructor เตรียมโจทย์เขียนโปรแกรม ตัวอย่างการประเมิน และข้อมูลที่เกี่ยวข้อง

โปรเจกต์พัฒนาเป็น **modular monolith** ด้วย FastAPI และ Jinja2 ทุกโมดูลอยู่ในแอปเดียวกัน แต่แยกความรับผิดชอบและเจ้าของงานอย่างชัดเจน เพื่อให้สมาชิกในทีมพัฒนาแต่ละส่วนได้โดยไม่ผูกกันเกินไป

> สถานะปัจจุบันยังเป็น team scaffold ไม่ใช่ระบบที่เสร็จสมบูรณ์
>
> ฟีเจอร์ที่ใช้งานได้จริงมีเพียง Topics API ส่วน Assignment, AI และ Database ยังเป็นพื้นที่สำหรับทีมเจ้าของงาน

## เป้าหมายของ Scaffold

โปรเจกต์นี้ตั้งใจเปลี่ยน codebase ให้เป็น modular monolith ที่นักศึกษาในทีมอ่านและแบ่งงานกันได้ง่าย โดยมีองค์ประกอบหลักสี่อย่าง:

1. Core API ตัวอย่างหนึ่งชุดที่รันได้จริง
2. Placeholder ที่ระบุเจ้าของงานของฟีเจอร์ที่ยังไม่พัฒนาอย่างชัดเจน
3. Server-rendered layout กลางที่ทุกหน้าสามารถนำกลับมาใช้ได้
4. Tests ที่ช่วยรักษากฎของสถาปัตยกรรมเมื่อสมาชิกแต่ละคนเพิ่มโค้ด

สมาชิกทีมควรใช้ README นี้ตอบคำถามต่อไปนี้ได้โดยไม่ต้องอ่านโค้ดส่วนที่ไม่เกี่ยวข้อง:

1. ฟีเจอร์ที่รับผิดชอบควรอยู่ในโมดูลใด
2. โมดูลใดเป็นตัวอย่างรูปแบบ API และการแยกชั้นที่ทีมคาดหวัง
3. ต้องรัน tests และคำสั่งใดเพื่อพิสูจน์ว่างานพร้อมส่ง

## สถานะของแต่ละส่วน

| ส่วน                      | สถานะ                                     | ผู้รับผิดชอบ               |
| ------------------------- | ----------------------------------------- | -------------------------- |
| `core/topics`             | CRUD API ตัวอย่างที่รันได้จริง            | Foundation / Reference API |
| `core/assignments`        | Placeholder รอออกแบบและพัฒนา              | Assignment team            |
| `ai`                      | Placeholder รอ Assignment contract เสถียร | AI team                    |
| `database`                | Placeholder รอออกแบบฐานข้อมูล             | Database owner             |
| `web/templates/base.html` | Layout กลางของทุกหน้า                     | Design team                |

อย่า implement placeholder ของทีมอื่นโดยไม่ได้รับมอบหมาย เพราะแต่ละพื้นที่ตั้งใจเว้นไว้ให้เจ้าของงานเป็นผู้ออกแบบ contract และ implementation เอง

## ขอบเขตที่ยังไม่ทำ

เพื่อให้แต่ละทีมยังเป็นเจ้าของการออกแบบของตนเอง scaffold ปัจจุบันจึงตั้งใจ **ไม่รวม** สิ่งต่อไปนี้:

- Assignment และ Test Case CRUD
- AI generation, provider integration, RAG, embeddings หรือ PDF ingestion
- Database schema, migration, ORM หรือการรับประกันการจัดเก็บข้อมูล
- Authentication, authorization, course management, document upload, analytics หรือ grading
- Browser JavaScript ที่ทีมเขียนเอง
- การรองรับ schema หรือข้อมูลจาก AI/database implementation รุ่นเก่า

รายการเหล่านี้ไม่ใช่ฟีเจอร์ที่ถูกลืม แต่เป็นงานในอนาคตที่ต้องเริ่มจาก contract หรือ task ของทีมเจ้าของงานก่อน

## คำศัพท์ที่ใช้ในโปรเจกต์

ใช้คำศัพท์เหล่านี้ให้เหมือนกันทั้งในโค้ด API เอกสาร และหน้าจอ

| คำศัพท์        | ความหมาย                                                                                | หลีกเลี่ยงการใช้คำว่า     |
| -------------- | --------------------------------------------------------------------------------------- | ------------------------- |
| **Instructor** | ผู้สร้างและดูแลโจทย์เขียนโปรแกรม                                                        | Teacher, Admin, User      |
| **Assignment** | โจทย์เขียนโปรแกรม ประกอบด้วยรายละเอียด เงื่อนไข และ Test Cases                          | Challenge, Task, Question |
| **Test Case**  | คู่ของ input และ expected output ซึ่งต้องเป็นของ Assignment เสมอ                        | Example, Check            |
| **Topic**      | หัวข้อความรู้ที่ Assignment สามารถอ้างอิงได้ เช่น Array, Graph หรือ Dynamic Programming | Tag, Category, Label      |

## เทคโนโลยีที่ใช้

- Python 3.12 ขึ้นไป
- FastAPI สำหรับ HTTP API
- Jinja2 สำหรับ HTML template
- Uvicorn สำหรับรันแอป
- uv สำหรับจัดการ dependency และ virtual environment
- Pytest สำหรับทดสอบ
- Ruff สำหรับ lint และตรวจรูปแบบโค้ด
- Tailwind CSS สำหรับ styling

ขณะนี้ระบบยังไม่มี database client, ORM, migration, AI provider หรือ external service dependency

## เริ่มใช้งานแบบ Local

สิ่งที่ต้องติดตั้งก่อน:

- Python 3.12 ขึ้นไป
- [uv](https://docs.astral.sh/uv/)

ติดตั้ง dependencies:

```bash
uv sync
```

เปิด development server:

```bash
uv run fastapi dev src/greader/main.py
```

เมื่อ server เริ่มทำงานแล้ว เปิด URL ต่อไปนี้:

| URL                                   | หน้าที่                            |
| ------------------------------------- | ---------------------------------- |
| <http://127.0.0.1:8000/>              | หน้าเว็บตัวอย่างที่ใช้ layout กลาง |
| <http://127.0.0.1:8000/health>        | ตรวจว่าแอปยังทำงานอยู่             |
| <http://127.0.0.1:8000/docs>          | Swagger UI สำหรับทดลอง API         |
| <http://127.0.0.1:8000/openapi.json>  | OpenAPI specification              |
| <http://127.0.0.1:8000/api/v1/topics> | Topics API                         |

หยุด server ด้วย `Ctrl+C`

## โครงสร้างโปรเจกต์

```text
greader/
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile
│
├── docs/
│   ├── adr/
│   │   ├── 0001-reset-to-core-schema.md
│   │   ├── 0002-use-topics-as-the-reference-slice.md
│   │   └── 0003-use-neon-and-r2-for-future-database.md
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
    └── unit/
```

### ไฟล์ระดับโปรเจกต์

| ไฟล์             | หน้าที่                                                              |
| ---------------- | -------------------------------------------------------------------- |
| `README.md`      | ภาพรวม วิธีเริ่มใช้งาน โครงสร้าง คำศัพท์ ownership และกติกาหลัก      |
| `pyproject.toml` | Dependencies และ configuration ของ Pytest, Ruff และ Coverage         |
| `uv.lock`        | ล็อก dependency versions เพื่อให้ทุกเครื่องติดตั้งเหมือนกัน          |
| `Dockerfile`     | วิธีสร้าง production container                                       |
| `docs/adr/`      | เหตุผลของการตัดสินใจด้านสถาปัตยกรรมที่ไม่ควรเปลี่ยนโดยไม่หารือกับทีม |

### `src/greader/main.py`

`main.py` เป็น **composition root** มีหน้าที่ประกอบส่วนต่าง ๆ ของแอปเท่านั้น เช่น:

- สร้าง FastAPI application
- mount static files
- ตั้งค่า Jinja2 templates
- สร้าง repository และ service
- เก็บ service ไว้ใน application state
- include API router
- ประกาศ route ระดับแอป เช่น `/` และ `/health`

ห้ามใส่ business rule, SQL, database operation หรือ AI workflow ลงในไฟล์นี้

ฟังก์ชัน `create_app()` รองรับการส่ง repository จากภายนอก ทำให้ test สามารถสร้างแอปที่มี state แยกจากกันได้

## รูปแบบสถาปัตยกรรมของ Core module

Topics เป็น reference implementation สำหรับโมดูล Core อื่น ๆ

```text
HTTP request
    ↓
routes.py
    ↓
service.py
    ↓
repository interface
    ↓
in-memory หรือ database adapter
```

หน้าที่ของแต่ละไฟล์:

| ไฟล์            | หน้าที่                                                         | ไม่ควรมี                     |
| --------------- | --------------------------------------------------------------- | ---------------------------- |
| `models.py`     | Domain model และคำศัพท์ทางธุรกิจ                                | FastAPI, ORM, storage client |
| `schemas.py`    | Request/response schema ที่แสดงใน OpenAPI                       | Business workflow            |
| `repository.py` | Interface สำหรับอ่านและบันทึกข้อมูล รวมถึง adapter              | HTTP handling                |
| `service.py`    | Use case และ business rule                                      | FastAPI, ORM, SQL            |
| `routes.py`     | รับ HTTP request เรียก service และแปลง error เป็น HTTP response | Business rule หรือ SQL       |

Dependency ควรไหลจาก adapter เข้าหา domain ไม่ใช่ให้ domain รู้จัก framework หรือฐานข้อมูล

### ทิศทางของ Dependency

```text
main → web templates/static files
main → core.topics routes
core.topics routes → service → repository interface + domain
in-memory adapter → repository interface + domain
future AI → Core domain
Core ─X→ AI
future database adapter → Core repository interface
Core service ─X→ database technology
```

`main.py` เป็นจุดประกอบ dependency และลงทะเบียน routes ส่วน domain และ service ต้องไม่รู้จัก FastAPI, ORM หรือ storage technology

## Topics API

Topics API เป็น CRUD reference ที่ทำงานได้โดยไม่ต้องมีฐานข้อมูล

| Method   | Path                        | ความหมาย           | สำเร็จ |
| -------- | --------------------------- | ------------------ | ------ |
| `POST`   | `/api/v1/topics`            | สร้าง Topic        | `201`  |
| `GET`    | `/api/v1/topics`            | ดู Topic ทั้งหมด   | `200`  |
| `GET`    | `/api/v1/topics/{topic_id}` | ดู Topic เดียว     | `200`  |
| `PUT`    | `/api/v1/topics/{topic_id}` | แทนที่ข้อมูล Topic | `200`  |
| `DELETE` | `/api/v1/topics/{topic_id}` | ลบ Topic           | `204`  |

ตัวอย่างสร้าง Topic:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/topics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Graphs",
    "description": "Network problems"
  }'
```

กฎของ Topic:

- `name` ห้ามเป็นค่าว่าง
- `name` ยาวได้ไม่เกิน 80 ตัวอักษร
- `description` ยาวได้ไม่เกิน 500 ตัวอักษร
- ระบบตัดช่องว่างด้านหน้าและด้านหลัง
- Topic name ห้ามซ้ำโดยไม่สนตัวพิมพ์เล็กหรือใหญ่
- `PUT` เป็นการ replace ข้อมูลทั้งหมด ไม่ใช่ partial update
- รายการ Topic ถูกเรียงตามชื่อ
- ID ถูกสร้างเป็น UUID

Error ที่ service แปลงเป็น HTTP response:

| สถานการณ์                         | Status | Error code               |
| --------------------------------- | ------ | ------------------------ |
| ไม่พบ Topic                       | `404`  | `topic_not_found`        |
| ชื่อ Topic ซ้ำ                    | `409`  | `topic_name_conflict`    |
| Request ไม่ผ่าน schema validation | `422`  | FastAPI validation error |

ข้อมูล Topic ถูกเก็บใน memory ของ process จึงหายเมื่อ restart server และไม่ควรถูกมองว่าเป็น database contract ตัวจริง

## Assignment module

เริ่มที่:

```text
src/greader/core/assignments/README.md
```

โมดูลนี้ยังเป็น placeholder ทุกไฟล์มีเพียงคำอธิบายหน้าที่ ยังไม่มี model, schema, CRUD หรือ route ที่ใช้งานได้จริง

ลำดับที่แนะนำ:

1. ตกลง use case และ API contract ของ Assignment กับ Test Case
2. กำหนด domain model โดยให้ Assignment เป็นเจ้าของ Test Cases
3. กำหนด repository operations จาก use case ที่จำเป็น
4. เขียน service และ business rules
5. เขียน request/response schemas
6. เพิ่ม routes ใต้ `/api/v1/`
7. ใช้ in-memory adapter ก่อน
8. เขียน unit และ integration tests
9. ให้ Database owner เพิ่ม database adapter ภายหลัง

อย่าออกแบบ database schema ภายใน service และอย่า import AI จาก Core

## AI module

เริ่มที่:

```text
src/greader/ai/README.md
```

AI module ยังไม่มี feature, provider, route, database record หรือ configuration

เริ่มพัฒนาเมื่อ Assignment domain contract เสถียรแล้ว:

1. เลือก use case ให้ชัดก่อนเลือก AI provider
2. AI สามารถ import Core domain model ได้
3. Core ห้าม import `greader.ai`
4. แยก provider หลัง interface เพื่อให้เปลี่ยน provider ได้
5. ใช้ fake provider ใน test
6. ห้ามให้ automated test เรียก provider จริง

Dependency direction ที่อนุญาต:

```text
AI → Core domain
```

Dependency direction ที่ห้าม:

```text
Core → AI
```

## Database module

เริ่มที่:

```text
src/greader/database/README.md
```

สถานะปัจจุบันยังไม่มี schema, migration, credential หรือ database adapter

แนวทางที่ตกลงไว้:

```text
FastAPI → Neon PostgreSQL  สำหรับ structured data
FastAPI → Cloudflare R2    สำหรับ PDF และ uploaded objects
```

ฐานข้อมูลเก็บเฉพาะ object key และ metadata ของไฟล์ ส่วนไฟล์จริงเก็บใน R2

เมื่อเริ่มงาน database:

1. Database owner ออกแบบ Core schema หนึ่งชุด
2. สร้าง migration หลัง schema ได้รับการตกลง
3. เพิ่ม adapter หลัง repository interface ของ Core module
4. ให้ service พึ่ง repository interface เหมือนเดิม
5. จัดการ connection และ credentials ที่ขอบระบบ
6. อย่าให้ Core service import ORM หรือ storage client โดยตรง

การเลือก Neon และ R2 เป็นแนวทางในอนาคต ไม่ได้หมายความว่าสามารถเพิ่ม schema, client, migration หรือ credentials ได้ทันทีโดยไม่มี task

## Web และ Design

ไฟล์ layout กลาง:

```text
src/greader/web/templates/base.html
```

หน้าอื่นควรใช้ Jinja inheritance:

```jinja2
{% extends "base.html" %}
```

`base.html` รับผิดชอบองค์ประกอบร่วม เช่น:

- HTML document structure
- `<head>` และ metadata
- global stylesheet
- header และ navigation
- content block กลาง

Design team ควรแก้ shared layout ที่ `base.html` เพียงจุดเดียว แล้วให้หน้าอื่น inherit ต่อไป

### Tailwind CSS

แก้ source ที่:

```text
src/greader/web/static/css/input.css
```

จากนั้น compile ไปที่:

```text
src/greader/web/static/css/app.css
```

คำสั่ง build หลังติดตั้ง Tailwind standalone CLI แล้ว:

```bash
tailwindcss \
  -i src/greader/web/static/css/input.css \
  -o src/greader/web/static/css/app.css \
  --minify
```

โปรเจกต์ไม่ได้ใช้ Node หรือ npm สำหรับ Tailwind และใน repository ยังไม่ได้จัดการติดตั้ง Tailwind CLI ให้อัตโนมัติ

ควรแก้ `input.css` แล้ว generate `app.css` ใหม่ แทนการแก้ compiled CSS โดยตรง

### ข้อจำกัดเรื่อง JavaScript

HTML template ที่ทีมเขียนห้ามมี:

- `<script>` element
- `javascript:` URL
- inline event handler เช่น `onclick`, `onload` หรือ `onchange`

Swagger ที่ `/docs` ใช้ JavaScript ภายในของ FastAPI ได้ เพราะเป็น developer tooling ไม่ใช่ project-authored feature template

มี architecture test ตรวจข้อห้ามนี้อัตโนมัติ

## Tests

โครงสร้าง tests แบ่งตามระดับ:

```text
tests/
├── architecture/
├── integration/
└── unit/
```

### Unit tests

อยู่ใน `tests/unit/` ใช้ตรวจ domain rule, service และ repository โดยไม่ผ่าน HTTP

### Integration tests

อยู่ใน `tests/integration/` ใช้ตรวจ FastAPI ผ่าน ASGI transport โดยไม่ต้องเปิด server จริงหรือเรียก external service

### Architecture tests

อยู่ใน `tests/architecture/` ใช้ป้องกันกฎสำคัญ เช่น:

- Core ห้าม import AI
- Assignment placeholder ต้อง import ได้
- Template ที่ทีมเขียนห้ามมี browser JavaScript

## ตรวจคุณภาพก่อนส่งงาน

รันทุกคำสั่งนี้ก่อน commit หรือส่ง Pull Request:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

สถานะล่าสุดของ scaffold:

```text
12 tests passed
Ruff check passed
Ruff format check passed
```

หาก format check ไม่ผ่าน สามารถจัดรูปแบบไฟล์ด้วย:

```bash
uv run ruff format .
```

จากนั้นรัน quality gate ทั้งสามคำสั่งอีกครั้ง

## ควรเริ่มแก้งานจากตรงไหน

### ถ้ารับผิดชอบ Assignment

เริ่มที่:

```text
src/greader/core/assignments/README.md
```

จากนั้นดู `core/topics` เป็นตัวอย่างโครงสร้าง แต่ห้าม copy domain rule ของ Topic มาเป็น Assignment โดยไม่ออกแบบ use case ก่อน

### ถ้ารับผิดชอบ AI

เริ่มที่:

```text
src/greader/ai/README.md
```

รอ Assignment contract เสถียรก่อนสร้าง integration ที่พึ่ง Assignment

### ถ้ารับผิดชอบ Database หรือ Storage

เริ่มที่:

```text
src/greader/database/README.md
docs/adr/0001-reset-to-core-schema.md
docs/adr/0003-use-neon-and-r2-for-future-database.md
```

อย่าเพิ่ม schema หรือ migration จนกว่าจะได้รับ task และตกลง Core schema แล้ว

### ถ้ารับผิดชอบหน้าเว็บหรือ Design

เริ่มที่:

```text
src/greader/web/templates/base.html
src/greader/web/static/css/input.css
```

รักษา Jinja inheritance และข้อห้าม browser JavaScript

### ถ้าต้องการเข้าใจรูปแบบ Backend

อ่านตามลำดับ:

```text
core/topics/models.py
→ core/topics/repository.py
→ core/topics/service.py
→ core/topics/schemas.py
→ core/topics/routes.py
→ main.py
→ tests/
```

ลำดับนี้ทำให้เห็น domain และ use case ก่อนเห็นรายละเอียด HTTP

## ขั้นตอนเพิ่มฟีเจอร์ใหม่

1. ตรวจว่า feature อยู่ใน ownership ของทีมใด
2. อ่าน ADR และ README ของ module นั้น
3. เขียน use case และ public contract ให้ชัด
4. กำหนด domain model โดยไม่ผูกกับ FastAPI หรือ database
5. กำหนด repository interface จากสิ่งที่ service ต้องใช้
6. เขียน service และ business rules
7. เขียน HTTP schemas และ routes ใต้ `/api/v1/`
8. ประกอบ dependency ใน `main.py`
9. เขียน unit tests ที่ service/repository seam
10. เขียน integration tests ที่ HTTP และ OpenAPI
11. รัน quality gate
12. อัปเดต README, module guide และ ownership table เมื่อขอบเขตเปลี่ยน

## สิ่งที่ต้องระวัง

- อย่าแก้หรือ implement placeholder ของทีมอื่นโดยไม่ได้รับมอบหมาย
- อย่าใส่ business rule ใน route หรือ `main.py`
- อย่าให้ domain หรือ service import FastAPI
- อย่าให้ Core import AI
- อย่าให้ service import ORM, SQL หรือ storage client
- อย่าเพิ่ม database schema หรือ migration โดยไม่มี task
- อย่าถือว่า in-memory Topic model คือ database schema ที่ตกลงแล้ว
- อย่าเพิ่ม API นอก `/api/v1/`
- อย่าเรียก database หรือ AI provider จริงจาก automated tests
- อย่าใส่ browser JavaScript ใน template ที่ทีมเขียน
- อย่า commit credential, API key หรือ connection string
- อย่าแก้ `app.css` โดยตรงถ้ายังสามารถแก้ Tailwind source และ build ใหม่ได้
- เมื่อเปลี่ยน public contract ต้องอัปเดต OpenAPI tests และเอกสารด้วย

## เอกสารการตัดสินใจ

ADR ใน `docs/adr/` บันทึกเหตุผลของการตัดสินใจสำคัญ:

- `0001-reset-to-core-schema.md` — ยังไม่เก็บ schema หรือ migration เก่า และใช้ in-memory จนกว่า Database owner จะออกแบบ Core schema
- `0002-use-topics-as-the-reference-slice.md` — ใช้ Topics เป็น executable reference เพียงชุดเดียว
- `0003-use-neon-and-r2-for-future-database.md` — เลือก Neon สำหรับ structured data และ R2 สำหรับ object storage ในอนาคต

หากต้องการเปลี่ยนการตัดสินใจเหล่านี้ ควรตกลงกับทีมและเพิ่มหรือแก้ ADR แทนการเปลี่ยน implementation อย่างเงียบ ๆ

### นโยบายไฟล์ใหม่

`.gitignore` ตั้งให้ ignore ไฟล์ใหม่ทั้งหมดตามขอบเขตที่ตกลงไว้ โดยมีข้อยกเว้นเฉพาะ `README.md`, `.env.example` และ `.gitignore` เอง ไฟล์ที่ Git ติดตามอยู่แล้วจะยังถูกติดตามต่อไปจนกว่าจะสั่งเอาออกจาก index โดยตรง

## Definition of Done

งานหนึ่งถือว่าเสร็จเมื่อ:

- API อยู่ใต้ `/api/v1/`
- Public contract แสดงใน Swagger/OpenAPI
- Domain และ service ไม่ขึ้นกับ FastAPI, ORM หรือ storage client
- Route ไม่มี business rule หรือ SQL
- มี unit tests สำหรับ service และ repository seam
- มี integration tests สำหรับ HTTP endpoint
- Test ไม่เรียก external provider หรือ database จริง
- Architecture tests ยังผ่าน
- เอกสารและ ownership table เป็นปัจจุบัน
- `pytest`, Ruff lint และ Ruff format check ผ่านทั้งหมด

## เกณฑ์ยอมรับของ Scaffold

Scaffold นี้ถือว่าพร้อมใช้งานเมื่อ:

1. Clone ใหม่ติดตั้งและเริ่มแอปได้โดยไม่ต้องมี database หรือ AI key
2. หน้า `/` แสดง shared layout และ template ที่ทีมเขียนไม่มี JavaScript
3. `/docs` แสดง Topic CRUD ครบห้า operation
4. Topic CRUD ทำงานใน memory และข้อมูลหายหลัง restart แอป
5. Assignment และ AI มีเพียง guidance ไม่มี feature route
6. ไม่มี implementation ของ AI, SQLAlchemy, Alembic, database schema หรือ migration ที่อยู่นอกขอบเขต
7. Tests ป้องกัน API behavior, import direction และกฎห้ามมี browser JavaScript
8. `README.md` และ ADR อธิบายสถานะและ ownership ตรงกับโค้ด
9. ผ่าน quality gate ทั้ง Pytest และ Ruff

## การเปลี่ยนผ่าน

Scaffold นี้ไม่รับประกันการเก็บ runtime data หรือ schema เดิมไว้ Database owner จะเพิ่ม Core schema และ adapters ภายหลังเป็น workstream แยกที่ผ่านการ review; จนกว่าจะถึงตอนนั้น application state จะเป็น in-memory เท่านั้น
