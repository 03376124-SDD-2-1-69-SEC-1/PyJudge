# GReader

**ภาษา:** [English](README.md) | ภาษาไทย

GReader คือแอปพลิเคชัน FastAPI ที่ช่วยผู้สอนเตรียมโจทย์เขียนโปรแกรม ชุดทดสอบ
และสื่อการเรียนที่เกี่ยวข้อง โปรเจกต์ใช้สถาปัตยกรรมแบบ modular monolith
เพื่อให้แต่ละทีมพัฒนาส่วนที่รับผิดชอบได้โดยไม่ผูกกับส่วนอื่นมากเกินไป

ขณะนี้โปรเจกต์ยังอยู่ระหว่างการพัฒนา Topics API เป็นฟีเจอร์อ้างอิง
ส่วนโมดูล Assignment และ AI ยังอยู่ระหว่างการพัฒนา ข้อมูล Topic
ถูกเก็บไว้ในหน่วยความจำและจะหายเมื่อรีสตาร์ตเซิร์ฟเวอร์

## เริ่มต้นใช้งาน

### 1. Clone Repository

```bash
git clone https://github.com/03376124-SDD-2-1-69-SEC-1/PyJudge.git
cd PyJudge
```

หากระบบไม่รู้จักคำสั่ง `git` ให้ติดตั้งตามหัวข้อถัดไป แล้วจึงรันคำสั่ง clone
อีกครั้ง

### 2. ตรวจสอบเครื่องมือที่จำเป็น

โปรเจกต์ต้องใช้ Git, `uv` และ Python 3.12 ขึ้นไป

#### macOS

เปิด Terminal แล้วรัน:

```bash
git --version
uv --version
python3 --version
```

ติดตั้งเครื่องมือที่ยังไม่มี:

```bash
# Git (Apple Command Line Tools)
xcode-select --install

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Python 3.12 ที่จัดการโดย uv
uv python install 3.12
```

#### Windows

เปิด PowerShell แล้วรัน:

```powershell
git --version
uv --version
py --version
```

ติดตั้งเครื่องมือที่ยังไม่มีด้วย WinGet:

```powershell
# Git
winget install --id Git.Git -e --source winget

# uv
winget install --id astral-sh.uv -e

# Python 3.12 ที่จัดการโดย uv
uv python install 3.12
```

หลังติดตั้งเครื่องมือให้เปิด Terminal หรือ PowerShell ใหม่ แล้วตรวจสอบเวอร์ชัน
อีกครั้ง สามารถดูวิธีติดตั้งทางเลือกได้จากหน้าอย่างเป็นทางการของ
[Git](https://git-scm.com/install/) และ
[`uv`](https://docs.astral.sh/uv/getting-started/installation/)

### 3. ติดตั้ง Dependencies

รันคำสั่งนี้ภายในไดเรกทอรีของโปรเจกต์:

```bash
uv sync
```

`uv` จะสร้าง virtual environment และติดตั้ง dependencies ตาม lockfile
โดยไม่จำเป็นต้อง activate environment เมื่อใช้คำสั่ง `uv run`

### 4. ตั้งค่า Environment

สร้างไฟล์ `.env` จากไฟล์ตัวอย่าง

บน macOS:

```bash
cp .env.example .env
```

บน Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

เปิดไฟล์ `.env` แล้วกรอก credentials ที่ได้รับจากทีม ปัจจุบันแอปต้องใช้
การเชื่อมต่อ Neon PostgreSQL ใน `DATABASE_URL` และค่า Cloudflare R2 ต่อไปนี้:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@host/database?sslmode=require
R2_ENDPOINT_URL=
R2_BUCKET_NAME=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
```

กำหนด `GEMINI_API_KEY` เมื่อต้องพัฒนา Gemini integration ห้าม commit ไฟล์
`.env` หรือใส่ credentials จริงลงใน `.env.example`

### 5. รัน Database Migrations

```bash
uv run --env-file .env alembic upgrade head
```

### 6. เริ่ม Development Server

```bash
uv run --env-file .env uvicorn greader.main:app --reload
```

เปิด <http://127.0.0.1:8000> ในเบราว์เซอร์ หยุดเซิร์ฟเวอร์ด้วย `Ctrl+C`

## URL ที่ใช้งานบ่อย

| URL | รายละเอียด |
|---|---|
| <http://127.0.0.1:8000/> | หน้าแรก |
| <http://127.0.0.1:8000/docs> | เอกสาร API แบบโต้ตอบ |
| <http://127.0.0.1:8000/api/v1/topics> | Topics API |
| <http://127.0.0.1:8000/health> | สถานะแอปพลิเคชัน |
| <http://127.0.0.1:8000/health/db> | สถานะ Neon PostgreSQL |
| <http://127.0.0.1:8000/health/r2> | สถานะ Cloudflare R2 |

## คำสั่งสำหรับพัฒนา

รันชุดทดสอบ:

```bash
uv run --env-file .env pytest
```

ตรวจสอบ lint และรูปแบบโค้ด:

```bash
uv run ruff check .
uv run ruff format --check .
```

สร้าง migration หลังแก้ไข database models:

```bash
uv run --env-file .env alembic revision --autogenerate -m "describe the change"
```

## โครงสร้างโปรเจกต์

```text
sgreader/
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile
│
├── docs/
│
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
    └── unit/     # Unit, integration และ architecture tests
```

## เทคโนโลยีที่ใช้

- Python 3.12+
- FastAPI และ Uvicorn
- SQLModel, SQLAlchemy และ Alembic
- Neon PostgreSQL
- Cloudflare R2 และ Boto3
- Jinja2
- Pytest และ Ruff
- `uv` สำหรับจัดการ Python และ dependencies
