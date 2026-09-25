# Task scope

Maps a TASK-ID to who owns it, what state it is in, which paths it may touch,
and what "done" means. Read by `/start-task` and `/grill-me`. Keep in sync with
the team board. This file is the only list of tasks; there are no duplicate
GitHub Issues.

This is a single app (ADR-0007): one FastAPI process, one repo, one Neon
project with schemas `core` and `rag`. Modules call each other through Python
interfaces. The AI side lives in `src/greader/ai/`. Paths below are relative
to `src/greader/` unless they start with `tests/`, `docs/`, `scripts/`,
`alembic/`, `.github/` or name a file at the repo root.

## Columns

- **Status** is `open`, `in-progress` or `done` and nothing else.
  `/start-task` reads only this column. It offers `open` rows owned by the
  person running it or by `TBD` (shown as "ยังไม่มีเจ้าของ รับได้"), and
  `in-progress` rows owned by the person running it. A branch existing or not
  never decides a row's state. `OPS-*` and `BUG-*` are patterns, not tasks:
  their Status is `—` and they are never offered.
- **May touch** lists paths that must already exist. A path the task has to
  create goes in its own segment, `creates: ...`, so `/start-task` does not
  count it as missing. A row with a missing path, or wording from the retired
  two-service design, is hidden from friends and shown only to พาย (or with
  `--maintainer`) under "งานที่ต้องอัปเดต".
- **Done when** is written in Thai for a task still to do. SQL adapters are
  never listed in a slice's row; every one of them belongs to OPS-15.

Rows that were closed and no longer apply are in `docs/task-archive.md`.

| TASK-ID | Owner | Status | May touch | Done when |
|---|---|---|---|---|
| OPS-* | พาย | — | anything | varies, see board |
| CORE-01 | พาย + ฟิล์ม | done | `core/generation/schemas.py` | `core/generation/schemas.py` exists once in this repo. Done — merged in PR #3 |
| CORE-02 | พาย | done | `core/generation/routes.py`, `ai/client.py` | mock endpoint callable from outside. Done — merged in PR #4 |
| CORE-03 | พาย | done | `core/topics/`, `tests/` | merged to dev and runs |
| CORE-04 | นัด | done | `core/assignments/`, `tests/` | create, update, delete via API |
| CORE-05 | นัด | done | `core/assignments/testcase_routes.py`, `tests/` | linked to an assignment, deleted with it. Branch `feat/CORE-05-testcases-crud` is abandoned (not deleted): its last commit `8a55e56` builds a separate `core/test_cases/` slice, which conflicts with test cases living inside the Assignment aggregate (CORE-10, CORE-11) |
| CORE-06 | พาย | done | `database/storage/r2.py`, config | file uploads to R2 through an endpoint |
| FE-01 | โปรแกรม | done | `web/templates/base.html`, `web/static/css/input.css` | every page extends base |
| AI-01 | ฟิล์ม | done | `ai/` (domain and service, no ORM), `database/rag/vector_repository.py`, `tests/unit/ai/`, `tests/db/` | a vector inserted through the API comes back from a search, proven by a `postgres`-marked test against a real database |
| AI-02 | ฟิล์ม | open | `ai/`; creates: `ai/ingestion/` | ฟิล์มเลือก library แล้วแจ้งพายให้เพิ่มใน `pyproject.toml` (ตัวเลือก: `pymupdf` สำหรับ PDF ดิจิทัล; `pytesseract` พร้อม Tesseract และชุดภาษาไทยสำหรับหน้าสแกน ขึ้นกับตาราง digital/scan ของ DES-02). แล้วดึงข้อความรายหน้าจากไฟล์ทดสอบใน `tests/fixtures/pdfs/` ได้ |
| AI-03 | พาย + ฟิล์ม | open | `ai/`; creates: `ai/ingestion/chunking.py` | ขอบเขต chunk ตรงตามที่คาดใน ≥80% ของไฟล์ทดสอบ |
| AI-04 | ฟิล์ม | open | `ai/`; creates: `ai/ingestion/`, `ai/embeddings/` | ฟิล์มเลือก library แล้วแจ้งพายให้เพิ่มใน `pyproject.toml` (ตัวเลือก: `sentence-transformers` ด้วยโมเดลหลายภาษาที่ให้ 768 มิติ; หรือ `google-genai` เรียก `text-embedding-004`). แล้ว PDF หนึ่งไฟล์เข้าระบบครบ มี chunk และ vector ใน schema `rag` |
| AI-05 | ฟิล์ม | open | `ai/`; creates: `ai/retrieval/` | query ที่กรองแล้วคืน `source_id`, page, score |
| AI-06 | พาย | open | `ai/client.py`, `core/generation/ports.py`, `tests/unit/ai/test_client.py` | adapter จริงใน `ai/client.py` ที่ implement `GenerationClient` แทน `StubGenerationClient` และถูกเรียกในแอปเดียวผ่าน Python interface; ส่งร่างและ citations ตามสัญญา. เลือก provider ก่อน จึงระบุ library |
| AI-07 | ฟิล์ม | open | `ai/app/routes.py`, `ai/app/service.py`, `tests/` | ลบเอกสารแล้วไม่เหลือ chunk ค้างอยู่ |
| DES-02 | อุ้ม | open | `docs/`; creates: `tests/fixtures/pdfs/` | มีไฟล์ PDF ทดสอบใน `tests/fixtures/pdfs/` พร้อมตาราง digital/scan ใน `docs/` |
| DES-03 | อุ้ม | open | creates: `docs/test-scenarios.md` | เช็กลิสต์ที่ทำตามได้ ครอบคลุม flow Classroom ตาม ADR-0007 ตั้งแต่สมัคร เข้าห้อง สร้างและ publish โจทย์ ส่งงาน จนดูผล |
| BUG-* | varies | — | whatever the fix needs, nothing more | the failing scenario passes |
| OPS-08 | พาย | done | `docs/task-scope.md`, `AGENTS.md`, `docs/adr/`, `.gitignore` | the table matches the tree; every done-condition is checkable in one repo |
| CORE-08 | พาย + ฟิล์ม | done | `core/generation/schemas.py`, `ai/client.py`, `tests/unit/ai/test_client.py`, `tests/integration/test_generation_api.py` | a citation identifies its source document; an approved draft has a stable handle; invalid input is rejected |
| CORE-09 | พาย | done | `core/uploads/`, `database/core/knowledge_document_repository.py`, `tests/` | a citation's `document_id` resolves to the document's filename through Core |
| OPS-09 | พาย | done | `.github/`, `setup-branch-protection.sh`, `tests/conftest.py`, `tests/db/`, `pyproject.toml` pytest config, `.env.example`, `AGENTS.md`, `docs/task-scope.md` | CI runs `tests/db/` against a Neon branch it creates and deletes per run; the canary reports RUN, not SKIPPED |
| CORE-10 | พาย | done | `database/core/assignment_repository.py`, `tests/db/` | test cases round-trip through `SQLAssignmentRepository.create`/`update`/`delete` as part of the assignment aggregate (see CORE-11); a `postgres`-marked test proves it in `tests/db/test_assignment_repository.py`. Done — see refactor/OPS-12-real-persistence |
| OPS-10 | พาย | done | `.github/workflows/ci.yml`, `database/storage/safety.py`, `scripts/ci_r2_cleanup.py`, `tests/r2/`, `tests/unit/test_r2_safety.py`, `tests/conftest.py`, `pyproject.toml`, `AGENTS.md`, `README.md` | `tests/r2/` runs in CI against the real `greader-ci` bucket, not skipped; presigned-URL fetch, multipart upload, and a conditional-write conflict are each proven against real R2 |
| OPS-11 | พาย | done | `docs/task-scope.md`, `AGENTS.md`, `pyproject.toml` | a row that owns a slice can mount it without an out-of-scope edit |
| CORE-11 | พาย | done | `core/assignments/`, `tests/` | the domain layer holds no field that exists only to satisfy a table; the contract test covers parent/child containment |
| OPS-12 | พาย | done | anything | wired Assignments/Topics/Uploads to real Postgres and R2; removed every in-memory adapter from src/; fixed a pre-existing SQLModel mapper bug in tables.py. Done — see refactor/OPS-12-real-persistence. |
| OPS-13 | พาย | done | `core/generation/__init__.py`, `core/generation/service.py`, `database/core/generation_repository.py`, `tests/fakes/generation.py`, `tests/contracts/generation_repository.py`, `tests/db/test_generation_repository.py`, `tests/db/conftest.py`, `tests/unit/core/generation/test_generation_repository_contract.py`, `tests/unit/core/generation/test_generation_service.py` | `__init__.py` no longer re-exports schema types under domain names; the JSON codec is public and shared by both adapters; a contract test proves the fake and SQL adapter round-trip identically; `generate()` marks a request failed if `create_artifact` raises, not only if the client call does |
| OPS-14 | พาย | done | `docs/adr/0007-classroom-centric-flow.md`, `CONTEXT.md`, `AGENTS.md`, `docs/task-scope.md`, `docs/wireframes/`, `docs/handoff/`, `tests/architecture/`; phase 2: `core/`, `integrations/`, `database/pending.py`, `web/templates/`, `main.py`, `scripts/demo.py`, `tests/` | ADR-0007 accepted; every new AGENTS.md rule has a test in `tests/architecture/`; every route in the ADR's page and API contract exists on in-memory fakes and is covered by an integration test per role. Done — PR #29 and #31 merged |
| OPS-15 | พาย | open | `database/core/tables.py`, `database/rag/tables.py`, `alembic/versions/`, `database/core/*_repository.py`, `tests/db/` | the ADR-0007 "Schema changes" list is one hand-written migration that CI upgrades on its own Neon branch; each new slice has a SQL adapter passing its contract test, and this includes every adapter for the slices below; no new-slice handler returns 503 |
| OPS-16 | พาย | open | `ai/app/main.py`, `tests/unit/ai/`, `tests/integration/`, `tests/architecture/` | ลบ standalone AI app (`create_app` และ `create_production_app` ใน `ai/app/main.py`) ที่ไม่มีใครเรียกแล้ว เพราะ `vector_router` ถูก mount ใน `greader.main`; เทสต์ที่เคยสร้างแอปนี้ย้ายไปใช้แอปหลัก |
| CORE-12 | TBD | done | `core/auth/`, `tests/` | ลงทะเบียน (KMITL email), verify, login, logout, `current_actor(request)`, scrypt และ session ทำครบบน fakes พร้อมเทสต์ (OPS-14). การย้าย `VerificationMailer` ไปเรียก `NotificationService` เป็นงานของ CORE-18 |
| CORE-13 | TBD | open | `core/classrooms/`, `core/assignments/`, `core/submissions/`, `tests/` | ทุก use case ของ Classroom (สร้าง, เข้าด้วยรหัส, สร้างรหัสใหม่/ปิดรหัส, ลบ Member, archive/unarchive, summary) ทำบน fakes แล้ว เหลือ `summary.csv` และ `submissions.csv` พร้อม unit และ integration test; non-member ได้ 404, Student ทำ use case ของ Instructor ได้ 403 |
| CORE-14 | TBD | done | `core/assignments/`, `tests/` | Postings, Versions ที่ต้องมีเหตุผล, การขยาย deadline เฉพาะ Posting ที่เลือก, Test Case มี `kind` และ `note` ทำครบบน fakes พร้อมเทสต์ (OPS-14) |
| CORE-15 | TBD | done | `core/generation/`, `tests/` | Drafts ต่อ Classroom, stepper บันทึกทีละ step, regenerate ทีละส่วน, publish หลาย Classroom ผ่าน `AssignmentPublisher`, Quota รายวัน, ลบ `/api/v1/generations` ทำครบบน fakes (OPS-14). Quota ที่ปรับได้อยู่ใน CORE-19 และ `DocumentCatalog` จริงอยู่ใน CORE-16 |
| CORE-16 | TBD | open | `core/uploads/`, `tests/`; creates: `core/documents/` | เปลี่ยนชื่อ slice `core/uploads/` เป็น `core/documents/`; `/api/v1/documents` แสดงคลังของ Instructor พร้อมจำนวน "used in", retry, delete; ลบ `/api/v1/uploads`; เติม `DocumentCatalog` ให้ T-03. การแก้ import ใน `database/core/knowledge_document_repository.py` เป็นของพาย |
| CORE-17 | พาย | open | `core/submissions/`, `integrations/judge0.py`, `tests/` | รอ ADR-0007 open question 1/2. Run และ Submit, Late และ Closed, latest-counts ทำบน fakes ด้วย `StubCodeRunner` แล้ว เหลือ (a) adapter Judge0 CE จริง, Submit แบบ async และ sandbox (open question 1, issue #30); (b) ตัดสินคะแนนต่อ Submission ปัดลงหรือ half up (open question 2). `submissions.csv` อยู่ที่ CORE-13 |
| CORE-18 | TBD | open | `integrations/email.py`, `core/auth/`, `tests/`; creates: `core/notifications/` | แจ้งเตือนที่เก็บไว้ (Assignment updated/published, Notify students) พร้อม read และ read-all; "deadline tomorrow" คำนวณตอนอ่าน; `EmailSender` stub ใช้ทั้ง auth และ notifications; ชี้ `VerificationMailer` ของ auth ไปที่ `NotificationService` |
| CORE-19 | TBD | open | `core/generation/`, `tests/`; creates: `core/admin/` | approve/reject คำขอ Instructor, list/search/deactivate users, AI settings (model จาก allowlist ใน config, daily quota ที่ปรับได้แทนค่าคงที่ 20, max pages, require citations), สถานะบริการ 6 ตัว |
| FE-05 | TBD | done | `web/templates/shared/g*`, `core/auth/pages.py`, `web/static/css/input.css` | G-01, G-03, G-04 และ header G-02 มี template และเทสต์แล้ว (`tests/integration/test_auth_pages.py`). งาน UI ต่อใน UI-01 |
| FE-06 | TBD | done | `web/templates/shared/c*`, `core/classrooms/pages.py`, `web/static/css/input.css` | C-01, C-02, C-03 มี template และเทสต์แล้ว (`tests/integration/test_classroom_pages.py`). งาน UI ต่อใน UI-01 |
| FE-07 | พาย | open | `web/templates/student/`, `core/submissions/pages.py`, `web/static/css/input.css` | เหลือ S-02a (สถานะ Submit แบบ async) ซึ่งรอ CORE-17 (a). ส่วน UI ที่เหลือต่อใน UI-01 |
| FE-08 | TBD | open | `web/templates/instructor/`, `core/generation/pages.py`, `core/classrooms/pages.py`, `core/submissions/pages.py`, `web/static/css/input.css`; creates: `core/assignments/pages.py`, `web/templates/instructor/t05_edit.html`, `web/templates/instructor/t06_documents.html` | T-01 ถึง T-04 มีแล้ว เหลือ T-05 หน้าแก้ไข (`/classes/{id}/assignments/{aid}/edit` และ 05a ถามขยาย deadline), T-06 หน้าเอกสาร (คู่กับ CORE-16), T-02 search และปุ่ม "Notify students" หลัง CORE-18. แท็บเป็น URL, แต่ละ step ของ stepper เป็น form post แยก |
| FE-09 | TBD | open | `web/templates/admin/`, `web/static/css/input.css`; creates: `core/admin/pages.py` | A-01 สามแท็บ และ 01a/01b (มีแต่ `a01_placeholder.html`); สถานะระบบรีเฟรชด้วย `<meta http-equiv="refresh" content="60">`; ทำคู่กับ CORE-19 |
| UI-01 | พาย | open | `web/templates/`; creates: `docs/ui-audit.md` | เทียบ mock ใน Figma GradeFlow กับ template ใน `web/templates/` แล้วทำตารางใน `docs/ui-audit.md` (หน้า, template, Figma frame, ผล: ตรง / ไม่ตรง / ไม่มี mock) จากนั้นแตกหน้าที่ไม่ตรงเป็นงานย่อยให้เพื่อน. ต้องรอพายส่งรายชื่อ frame มาก่อน |

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
