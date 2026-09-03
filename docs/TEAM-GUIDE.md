# TEAM-GUIDE

คู่มือเริ่มต้นสำหรับทีม GReader กติกาละเอียดอยู่ที่ [`AGENTS.md`](../AGENTS.md)
และ [`docs/task-scope.md`](task-scope.md) — ไฟล์นี้ไม่ก็อปเนื้อหามาซ้ำ

## 1. วันแรก

```bash
git clone <repo-url>
cd greader
uv sync
uv run fastapi dev src/greader/main.py
```

เปิด `http://127.0.0.1:8000/health` ควรได้ `{"status": "ok", ...}`
เปิด `http://127.0.0.1:8000/docs` ควรเห็น endpoint ของ `core/topics`

ถ้าจะต่อ DB จริง ต้องคัดลอก `.env.example` เป็น `.env` แล้วขอค่า credential
จากพาย — ห้ามแก้ `.env.example` เอง

## 2. เริ่มงานหนึ่ง task

1. เช็ค TASK-ID ของตัวเองใน `docs/task-scope.md`
2. แตก branch จาก `dev` เท่านั้น ชื่อรูปแบบ `<type>/<TASK-ID>-<slug>`
   เช่น `feat/CORE-04-assignment-crud`
3. `<type>` เลือกจาก `feat`, `fix`, `chore`, `docs`, `refactor`

ห้าม commit ตรงเข้า `main` หรือ `dev`

## 3. กติกาอยู่ที่ไหน

| ไฟล์ | เก็บอะไร |
|---|---|
| `AGENTS.md` | กติกาที่ agent ต้องรู้ก่อนแตะโค้ด — stack, layering, ห้ามทำอะไรบ้าง |
| `docs/task-scope.md` | TASK-ID ไหน แตะไฟล์ไหนได้บ้าง ใครเป็นเจ้าของ |
| `CLAUDE.md` | แค่ `@AGENTS.md` (import บรรทัดเดียว) — **ห้ามแก้ไฟล์นี้** เนื้อหาจริงอยู่ที่ `AGENTS.md` ที่เดียว |

## 4. agent แต่ละตัวอ่านอะไร

- **Claude Code** — อ่าน `CLAUDE.md` (ซึ่ง import `AGENTS.md` อัตโนมัติ) และมีคำสั่ง
  `/grill-me` ให้ interview ตัวเองก่อนเริ่มเขียนโค้ด สั่งได้เลยในเซสชัน
- **agent ตัวอื่น** (Cursor, Windsurf, ฯลฯ) — ไม่มี `/grill-me` ให้ใช้
  เปิด `AGENTS.md` อ่านเองตอนเริ่มเซสชัน แล้วเปิด `docs/task-scope.md`
  หา row ของ TASK-ID ตัวเอง ก่อนแตะไฟล์ใดๆ

## 5. กติกาที่คนพลาดบ่อย

- โปรเจกต์นี้ **sync ล้วน** ห้าม `async def`, `AsyncSession`, driver แบบ async
- **ไม่ใช้ `Depends()`** สำหรับ service — route ดึง service จาก
  `request.app.state` แทน
- **ห้ามรัน alembic** (`upgrade`, `downgrade`, `--autogenerate`) หรือแก้ไฟล์
  migration เอง มีพายคนเดียวที่รันได้ เพราะ DB ใช้ร่วมกันทั้งทีม
- primary key ของตารางจริงเป็น `BIGSERIAL` (int) ไม่ใช่ UUID — UUID ใน
  `core/topics` เป็นแค่ demo in-memory ไม่ใช่ pattern ให้เลียนแบบ

## 6. quality gate ก่อนเปิด PR

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

รันไม่ผ่านอย่าเปิด PR ถ้า format ไม่ผ่าน ให้รัน `uv run ruff format .`
แล้วรันสามคำสั่งนี้ใหม่ทั้งหมด

## 7. เปิด PR

- target `dev` เท่านั้น
- ต้องมี approve อย่างน้อย 1 คนก่อน merge
- merge แบบ squash
- แตะไฟล์นอกเหนือ row ของตัวเองใน `docs/task-scope.md` ให้ทักในทีมก่อน ไม่ใช่
  เดาเอาเอง
