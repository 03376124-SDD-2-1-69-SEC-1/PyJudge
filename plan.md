# GReader Team Plan

สถานะ: team scaffold พร้อมแบ่งงาน

## หลักการร่วมกัน

- อ่าน CONTEXT.md, ADR, AGENTS.md และ README ของ module ก่อนแก้
- feature ใหม่อยู่ใต้ /api/v1/
- route → service → repository interface → adapter
- Core ห้าม import AI
- template ที่ทีมเขียนห้ามมี browser JavaScript
- ทุกงานรัน quality gate ก่อนส่ง

~~~bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
~~~

## Workstreams

| ทีม | Owned files | Deliverable | ห้ามทำ |
|---|---|---|---|
| Foundation | main.py, web/, tests/architecture/ | app composition, global layout, guards | implement Assignment/AI |
| Reference API | core/topics/, Topic tests | CRUD ตัวอย่างและ Swagger | เพิ่ม DB adapter |
| Assignment | core/assignments/ | Assignment + Test Case use cases/API/tests | import AI หรือกำหนด DB schema เอง |
| AI | ai/ | AI use case หลัง Assignment contract เสถียร | ให้ Core import AI |
| Database | persistence/ และ adapter ที่ตกลง | Neon schema/adapter/migration | เปลี่ยน Core service เป็น ORM |
| Design | web/templates/base.html, web/static/css/ | shared design system | เพิ่ม JavaScript ใน template |

## ลำดับงาน

1. Assignment team ตกลง API contract และ domain model
2. Assignment team ทำ in-memory CRUD/test ตาม Topics reference
3. Database owner ออกแบบ Core schema และ init Neon
4. Database owner เพิ่ม adapter หลัง repository seam
5. AI team เริ่มจาก Assignment domain contract ที่เสถียร
6. Design team ปรับ base.html และ CSS ให้ทุก page ใช้ร่วมกัน

## Definition of Done

- API ขึ้น Swagger และมี OpenAPI contract
- domain/service ไม่ import FastAPI หรือ database client
- integration tests ผ่านที่ HTTP seam
- tests ไม่เรียก external provider หรือ database จริง
- documentation และ ownership table อัปเดต
