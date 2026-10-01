# AI Module Placeholder

เจ้าของงาน: ทีม AI

AI อยู่ใน modular monolith เดียวกับ Core แต่ยังไม่มี feature, route, provider,
database record หรือ configuration ใน repository นี้

เมื่อเริ่มงาน:

1. อ่าน CONTEXT.md, docs/adr/, plan.md และ guide ของ Assignment
2. AI import Core domain model ที่เสถียรได้
3. Core ห้าม import AI
4. เลือก use case และ API contract ก่อนเพิ่ม provider หรือ dependency
5. เขียน test ที่ใช้ fake provider; ห้ามให้ test เรียก provider จริง
