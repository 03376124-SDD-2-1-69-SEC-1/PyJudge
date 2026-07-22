# PYJudge

**AI-assisted assignment authoring** — a web application for creating, managing, and grading assignments with the help of AI.

Built with [FastAPI](https://fastapi.tiangolo.com/), [Jinja2](https://jinja.palletsprojects.com/), and managed by [uv](https://docs.astral.sh/uv/).

---

## Project Structure

```
greader/
├── src/greader/              # Application package
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory (create_app)
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html         # Base layout
│   │   └── dashboard.html    # Dashboard page
│   └── static/               # Static assets (CSS, JS, images)
├── tests/                    # Test suite
│   └── test_app.py           # Integration tests
├── pyproject.toml            # Project config, dependencies, tool settings
└── README.md
```

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — fast Python package manager
- **Docker** — for the local PostgreSQL database

### Install uv

**macOS** (Homebrew):

```bash
brew install uv
```

or via the standalone installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows** (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

or via winget:

```powershell
winget install --id=astral-sh.uv -e
```

## Getting Started

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` to change PostgreSQL credentials, port, app port, or AI provider
settings. Leave `DATABASE_URL` blank to build the connection URL from
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, and
`POSTGRES_DB`. Set `DATABASE_URL` only when you need a full custom SQLAlchemy
URL.

### 2. Run with Docker

```bash
docker compose up --build
```

The compose app waits for PostgreSQL, runs Alembic migrations, then starts
GReader at **http://127.0.0.1:8000**.

### 3. Run locally with Docker PostgreSQL

Start only the database:

```bash
docker compose up -d db
```

Install dependencies:

```bash
uv sync
```

This installs both runtime and development dependencies and creates a `.venv` virtual environment automatically.

Run migrations:

```bash
uv run alembic upgrade head
```

Run the development server:

```bash
uv run uvicorn greader.main:app --reload
```

The app will be available at **http://127.0.0.1:8000**.

| Route        | Description                          |
| ------------ | ------------------------------------ |
| `GET /`      | Dashboard page                       |
| `GET /health`| Health-check endpoint (JSON)         |
| `GET /docs`  | Interactive API docs (Swagger UI)    |

## Testing

Run the full test suite:

```bash
uv run pytest -v
```

Run with coverage report:

```bash
uv run pytest --cov
```

## Linting & Formatting

Check for lint errors:

```bash
uv run ruff check .
```

Check formatting (no changes applied):

```bash
uv run ruff format --check .
```

Auto-fix and format:

```bash
uv run ruff check --fix .
uv run ruff format .
```

## License

This project is for educational purposes (KMITL).
