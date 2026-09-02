# Assignment Module Guide

เจ้าของงาน: ทีม Assignment

โมดูลนี้ตั้งใจเว้นไว้ให้ทีมออกแบบและเขียนเอง จึงไม่มี CRUD, route, schema หรือ
database implementation ซ่อนอยู่

## ก่อนเริ่ม

1. อ่าน CONTEXT.md เพื่อใช้คำว่า Assignment และ Test Case ให้ตรงกัน
2. อ่าน docs/adr/ และ plan.md เพื่อรู้ขอบเขตงาน
3. ดู core/topics เป็นตัวอย่างการแยก domain, HTTP schema, repository,
   service, route และ test

## หน้าที่ของไฟล์

| ไฟล์ | หน้าที่ |
|---|---|
| models.py | domain model ที่ไม่รู้จัก FastAPI หรือฐานข้อมูล |
| schemas.py | request/response contract ที่ Swagger แสดง |
| repository.py | seam สำหรับ in-memory และ database adapter ในอนาคต |
| service.py | use case และกฎของ Assignment/Test Case |
| routes.py | HTTP adapter แบบ versioned API |

## เงื่อนไขส่งงาน

- API อยู่ใต้ /api/v1/
- route ไม่มี business rule หรือ SQL
- service ไม่มี FastAPI/ORM import
- มี unit tests ที่ service/repository seam
- มี integration tests ที่ HTTP endpoint และ OpenAPI
- template ที่ทีมเขียนไม่มี script element, javascript URL หรือ inline event handler
- ก่อนส่งรัน uv run pytest, uv run ruff check . และ uv run ruff format --check .
