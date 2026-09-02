# GReader

**Language:** English | [ภาษาไทย](README.th.md)

GReader is a FastAPI application that helps instructors prepare programming
assignments, test cases, and related learning materials. It is organized as a
modular monolith so each team can develop its area without tightly coupling it
to the rest of the application.

The project is currently under development. The Topics API is the reference
feature, while the Assignment and AI modules are still being built. Topic data
is stored in memory and is cleared whenever the server restarts.

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/03376124-SDD-2-1-69-SEC-1/PyJudge.git
cd PyJudge
```

If `git` is not recognized, install it using the instructions in the next
section, then run the clone command again.

### 2. Check the Required Tools

The project requires Git, `uv`, and Python 3.12 or newer.

#### macOS

Open Terminal and run:

```bash
git --version
uv --version
python3 --version
```

Install any missing tools:

```bash
# Git (Apple Command Line Tools)
xcode-select --install

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Python 3.12 managed by uv
uv python install 3.12
```

#### Windows

Open PowerShell and run:

```powershell
git --version
uv --version
py --version
```

Install any missing tools with WinGet:

```powershell
# Git
winget install --id Git.Git -e --source winget

# uv
winget install --id astral-sh.uv -e

# Python 3.12 managed by uv
uv python install 3.12
```

Restart the terminal after installing a tool, then run the version checks
again. Alternative installers are available from the official
[Git](https://git-scm.com/install/) and
[`uv`](https://docs.astral.sh/uv/getting-started/installation/) pages.

### 3. Install the Project Dependencies

Run this command from the project directory:

```bash
uv sync
```

`uv` creates a local virtual environment and installs the locked dependencies.
You do not need to activate the environment when using `uv run`.

### 4. Configure the Environment

Create a local `.env` file from the template.

On macOS:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` and provide the credentials supplied by your team. The application
currently needs a Neon PostgreSQL connection in `DATABASE_URL` and these
Cloudflare R2 values:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@host/database?sslmode=require
R2_ENDPOINT_URL=
R2_BUCKET_NAME=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
```

Set `GEMINI_API_KEY` when working on Gemini integration. Never commit `.env` or
place real credentials in `.env.example`.

### 5. Apply Database Migrations

```bash
uv run --env-file .env alembic upgrade head
```

### 6. Start the Development Server

```bash
uv run --env-file .env uvicorn greader.main:app --reload
```

Open <http://127.0.0.1:8000> in your browser. Stop the server with `Ctrl+C`.

## Useful URLs

| URL | Description |
|---|---|
| <http://127.0.0.1:8000/> | Home page |
| <http://127.0.0.1:8000/docs> | Interactive API documentation |
| <http://127.0.0.1:8000/api/v1/topics> | Topics API |
| <http://127.0.0.1:8000/health> | Application health |
| <http://127.0.0.1:8000/health/db> | Neon PostgreSQL health |
| <http://127.0.0.1:8000/health/r2> | Cloudflare R2 health |

## Development Commands

Run the test suite:

```bash
uv run --env-file .env pytest
```

Check linting and formatting:

```bash
uv run ruff check .
uv run ruff format --check .
```

Create a migration after changing database models:

```bash
uv run --env-file .env alembic revision --autogenerate -m "describe the change"
```

## Project Structure

```text
src/greader/
├── main.py             # FastAPI application composition
├── core/
│   ├── topics/         # Reference Topics CRUD feature
│   └── assignments/    # Assignment module
├── ai/                 # AI integration area
├── database/           # Neon, SQLModel, Alembic, and R2 adapters
└── web/                # Jinja templates and static assets

alembic/                # Database migrations
tests/                  # Unit, integration, and architecture tests
```

## Technology Stack

- Python 3.12+
- FastAPI and Uvicorn
- SQLModel, SQLAlchemy, and Alembic
- Neon PostgreSQL
- Cloudflare R2 with Boto3
- Jinja2
- Pytest and Ruff
- `uv` for Python and dependency management
