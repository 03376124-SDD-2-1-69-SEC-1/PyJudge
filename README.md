# PYJudge

**AI-assisted assignment authoring** — a web application for creating, managing, and grading assignments with the help of AI.

Built with [FastAPI](https://fastapi.tiangolo.com/), [Jinja2](https://jinja.palletsprojects.com/), and managed by [uv](https://docs.astral.sh/uv/).

---

## Project Structure

```
greader/
├── src/greader/
│   ├── main.py               # Application factory and dependency wiring
│   ├── ai/                   # AI providers, schemas, services, persistence, routes
│   ├── assignments/          # Core assignment domain and HTTP routes
│   ├── templates/
│   │   ├── ai/               # Composer and artifact review pages
│   │   └── assignments/      # Assignment list and editor pages
│   └── static/css/           # Tailwind input and compiled stylesheet
├── alembic/                  # Database migrations
├── tests/                    # Unit and integration tests
├── pyproject.toml            # Dependencies and tool settings
└── README.md
```

The `ai` package is part of the same FastAPI monolith. It may import shared
assignment domain models, but it is not deployed as a separate service.
Rendered pages intentionally use no JavaScript; interactions use normal HTML
forms and POST-Redirect-GET.

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

| Route                              | Description                         |
| ---------------------------------- | ----------------------------------- |
| `GET /` or `GET /assistant`        | AI assignment composer              |
| `POST /assistant/generate`         | Generate a persisted draft          |
| `GET /assistant/artifacts/{id}`    | Review an AI-generated artifact     |
| `GET /assignments`                 | List saved assignments              |
| `GET /health`                      | Health-check endpoint               |
| `GET /docs`                        | Interactive API docs                |

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
