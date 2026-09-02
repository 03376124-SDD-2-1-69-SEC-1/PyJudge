# GReader Agent Guide

GReader เป็น modular monolith สำหรับงานกลุ่ม เป้าหมายปัจจุบันคือมี Core API
ตัวอย่างหนึ่งชุดและให้สมาชิกทีมเป็นเจ้าของ feature ที่เหลือ

## อ่านก่อนแก้

1. CONTEXT.md
2. docs/adr/
3. plan.md
4. README ของ module ที่รับผิดชอบ

## Ownership

| ส่วน | สถานะ | เจ้าของ |
|---|---|---|
| core/topics | runnable reference | Foundation/Reference API |
| core/assignments | placeholder | Assignment team |
| ai | placeholder | AI team |
| persistence | placeholder | Database owner |
| web/templates/base.html | shared layout | Design team |

อย่า implement placeholder ของทีมอื่น หากไม่ได้รับ task ชัดเจน

## Architecture Rules

- main.py เป็น composition root เท่านั้น
- domain/service ห้าม import FastAPI, ORM หรือ storage client
- Core ห้าม import greader.ai; AI import Core domain ได้ในอนาคต
- API ใหม่อยู่ใต้ /api/v1/
- browser JavaScript ห้ามอยู่ใน template ที่ทีมเขียน
- FastAPI /docs เป็น developer tooling และยกเว้นข้อห้าม browser JavaScript
- state ปัจจุบันเป็น in-memory; ห้ามเพิ่ม database/schema/migration โดยไม่มี task

## Quality Gate

ก่อน commit ให้รัน:

~~~bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
~~~
