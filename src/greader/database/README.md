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
