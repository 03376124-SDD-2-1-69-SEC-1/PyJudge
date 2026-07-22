# AGENTS.md

## Project Overview

You are building a web application named **Pytest**.

GReader is an instructor-first, AI-assisted programming assignment authoring platform for university instructors.

The system helps instructors:

- Write programming assignment descriptions.
- Define input and output formats.
- Define constraints and difficulty.
- Add a reference solution.
- Generate complete assignment drafts with AI.
- Generate candidate test cases and edge cases.
- Review generated content before saving it.
- Approve, reject, and edit candidate test cases.
- Detect missing edge cases and ambiguous requirements.
- Validate assignment completeness.
- Measure assignment quality before publishing.

GReader is not a student-focused online judge and must not look or behave like LeetCode.

The primary user in the current version is a university instructor.

---

## Current MVP Goal

The current goal is to deliver a working instructor-facing MVP for a live presentation.

The required MVP workflow is:

```text
Instructor enters a prompt
→ selects a generation mode
→ the server calls the configured AI provider
→ the AI returns structured data
→ the server validates the result with Pydantic
→ the instructor previews the generated content
→ the instructor explicitly saves the content
→ the saved assignment or test cases persist in the database
```

The current MVP supports these generation modes:

- `full_assignment`
- `test_cases`
- `edge_cases`

The MVP must allow an instructor to:

1. Open the AI Assistant page.
2. Enter a natural-language prompt.
3. Select what the AI should generate.
4. Select an existing assignment when context is required.
5. Generate structured assignment content.
6. Preview the generated result.
7. Save a complete assignment as a draft.
8. Save selected generated test cases as pending test cases.
9. Refresh or restart the server without losing saved data.

Generated content must never be published automatically.

The instructor remains responsible for final review and approval.

---

## Core Technology Stack

Use the following stack:

- Python 3.12
- `uv` for project and dependency management
- FastAPI
- Jinja2 server-rendered HTML templates
- Tailwind CSS
- Tailwind standalone CLI without Node.js or npm
- Minimal vanilla JavaScript
- SQLAlchemy 2.x
- Alembic
- SQLite for local development and automated tests
- PostgreSQL-compatible database configuration through `DATABASE_URL`
- Pydantic
- `pydantic-settings`
- Google Gen AI Python SDK through `google-genai`
- pytest
- FastAPI `TestClient`
- Playwright Python for future E2E testing
- Ruff for linting and formatting

---

## Prohibited Technologies

Do not introduce:

- React
- Vue
- Next.js
- Vite
- TypeScript
- Node.js
- npm
- A frontend SPA
- Supabase
- PocketBase
- MongoDB
- Firebase
- External authentication services
- LangChain
- LlamaIndex
- A second backend application
- Arbitrary Python code execution
- Student code execution
- AI-generated code execution

Do not add a dependency unless the active task explicitly requires it.

---

## Architecture Rules

Use a modular FastAPI monolith.

Keep these concerns separate:

- HTTP routes
- HTML templates
- application services
- domain models
- repositories
- SQLAlchemy persistence models
- AI provider implementations
- configuration

Do not place business logic directly in route functions or templates.

Use an application factory:

```python
def create_app(...) -> FastAPI:
    ...
```

Expose an application instance for Uvicorn:

```python
app = create_app()
```

Use dependency injection or `app.state` for repositories and services.

Tests must be able to create isolated application instances with test-specific dependencies.

Use paths relative to the installed Python package when locating templates and static files.

Do not depend on the current working directory for application resources.

---

## Persistence Rules

Use synchronous SQLAlchemy 2.x sessions for the current implementation.

Do not introduce `AsyncSession` during the MVP.

Use SQLite for:

- local development
- unit tests
- integration tests
- presentation demo data

Keep database configuration compatible with PostgreSQL by using:

```text
DATABASE_URL
```

Every database schema change must use Alembic.

Do not use `Base.metadata.create_all()` during normal application startup.

The normal application must use the SQLAlchemy repository.

The in-memory repository may remain available for focused unit tests.

Do not expose SQLAlchemy ORM objects directly to templates or business services when domain models already exist.

Use explicit mapping between persistence records and domain models.

---

## AI Provider Rules

Keep the AI provider behind an application-facing interface.

The application must support:

- a deterministic demo provider
- a Gemini provider

The demo provider must work without an API key.

Automated tests must use the demo provider or an injected fake provider.

Automated tests must never contact the real Gemini API.

The Gemini provider must use the official Python package:

```text
google-genai
```

Do not use LangChain or another agent framework.

AI provider selection must come from configuration.

Supported settings include:

```text
AI_PROVIDER
GEMINI_API_KEY
GEMINI_MODEL
AI_REQUEST_TIMEOUT_SECONDS
```

The default local provider should be:

```text
AI_PROVIDER=demo
```

When:

```text
AI_PROVIDER=gemini
```

the application must require a valid server-side `GEMINI_API_KEY`.

---

## Secret Management

The Gemini API key must be read from the server environment.

Do not save the API key in:

- the database
- cookies
- browser sessions
- HTML templates
- form fields
- query parameters
- audit logs
- normal application logs
- exception messages
- generated artifacts
- Git history

Never display any part of the API key in the browser.

The UI may display only a safe provider status such as:

```text
Demo provider active
Gemini connected
Gemini API key not configured
```

Do not build an API-key input form during the current MVP.

Keep `.env` ignored by Git.

Provide `.env.example` with empty secret values.

---

## Structured AI Output

AI-generated data must be validated with Pydantic before entering the domain or persistence layers.

Do not treat unrestricted AI text as trusted application data.

Do not manually extract JSON using regular expressions.

Do not depend on markdown code fences for structured output.

Use strict schemas and reject unexpected fields where practical.

A generated full assignment draft should contain:

- title
- problem statement
- input format
- output format
- constraints
- difficulty
- learning objectives
- reference solution
- examples
- candidate test cases
- ambiguity notes

A generated test case should contain:

- input data
- expected output
- category
- explanation

All generated content must remain a draft until explicitly saved by the instructor.

Never automatically publish generated content.

Never execute generated reference solutions during the current phase.

---

## Programming Assignment Scope

Version 1 supports Python 3.12 programming assignments only.

Assignments use the standard input/output model:

- A reference solution is a complete Python program.
- The program reads input from standard input.
- The program writes output to standard output.
- A test case contains plain-text input.
- A test case contains exact expected plain-text output.

The current MVP does not execute reference solutions or student submissions.

Generated test cases are candidate data only.

---

## Generation Modes

### Full Assignment

Internal value:

```text
full_assignment
```

Behavior:

- Does not require an existing assignment.
- Generates a complete assignment draft.
- Includes candidate test cases.
- Includes ambiguity notes.
- Does not save automatically.
- Can be explicitly saved as a draft assignment.

### Test Cases

Internal value:

```text
test_cases
```

Behavior:

- Requires an existing assignment.
- Uses the selected assignment as context.
- Generates normal and boundary test cases.
- Does not overwrite existing test cases.
- Generated cases remain previews until explicitly saved.
- Saved cases use pending review status.

### Edge Cases

Internal value:

```text
edge_cases
```

Behavior:

- Requires an existing assignment.
- Uses the selected assignment as context.
- Generates boundary, corner, or stress cases.
- Each generated case should explain the failure mode it targets.
- Generated cases remain previews until explicitly saved.
- Saved cases use pending review status.

---

## Instructor Review Rules

AI-generated assignments and test cases must be reviewed before becoming official data.

A generated artifact must have a clear state such as:

```text
draft
applied
discarded
```

Rules:

- A draft artifact may be previewed.
- A draft artifact may be explicitly applied.
- An applied artifact cannot be applied again.
- A discarded artifact cannot be applied.
- Applying an artifact must be transactional.
- The artifact must be marked as applied only after the database transaction succeeds.
- Refreshing a result page must not create duplicate assignments or test cases.

A complete AI-generated assignment must be saved with draft status.

AI-generated test cases must be saved with pending status.

---

## Duplicate Test Case Rules

Before saving generated test cases, normalize input and expected output.

Normalization must:

1. Convert CRLF newlines to LF.
2. Remove trailing whitespace from every line.
3. Remove final blank lines.
4. Preserve meaningful internal spaces.
5. Compare normalized input and normalized expected output together.

Do not silently insert duplicate test cases.

Duplicates should be skipped and reported safely to the instructor.

---

## Error Handling

Do not expose:

- stack traces
- raw provider responses
- internal exception details
- SQL errors
- system prompts
- API keys
- server configuration

Map AI provider failures to safe application error codes such as:

```text
provider_timeout
provider_authentication_failed
provider_rate_limited
provider_invalid_response
provider_unavailable
```

The browser must receive a clear and safe error message.

When practical, preserve the instructor's prompt after a failed request.

A failed generation request must not create a successful artifact.

---

## Frontend Rules

Frontend pages must use:

- Jinja2
- Tailwind CSS
- semantic HTML
- minimal vanilla JavaScript

Prefer:

- normal links
- normal HTML forms
- server-rendered validation
- POST-Redirect-GET for form mutations
- native `<select>`, `<textarea>`, `<input>`, and `<button>` controls

Use JavaScript only when server-rendered HTML cannot reasonably provide the interaction.

Examples of acceptable JavaScript:

- Showing or hiding the assignment selector based on generation mode.
- Populating a prompt textarea from a starter prompt.
- Small presentational interactions.

JavaScript must not become the source of truth for validation or application state.

Server-side validation is always authoritative.

---

## Design Direction

The interface must look like a professional instructor authoring workspace.

Use:

- an off-white or light-gray application background
- white panels
- subtle gray borders
- high-contrast typography
- generous whitespace
- soft rounded corners
- restrained accent colors
- clear draft, pending, applied, and discarded states

The application may be inspired by:

- Linear
- Vercel
- Notion
- GitHub

Do not use:

- student leaderboards
- competitive programming visuals
- flashy gradients
- game-like scoring
- online judge branding
- large casual chatbot bubbles

AI output should appear as a structured document preview, not as an informal chatbot response.

---

## Suggested Project Structure

Follow the existing repository structure first.

Do not restructure working code without a task-specific reason.

A preferred structure is:

```text
greader/
├── AGENTS.md
├── pyproject.toml
├── uv.lock
├── README.md
├── .python-version
├── .gitignore
├── .env.example
├── alembic.ini
├── alembic/
│   └── versions/
├── .tools/
│   └── tailwindcss
├── data/
├── src/
│   └── greader/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── web/
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   └── dependencies.py
│       ├── assignments/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── records.py
│       │   ├── mapping.py
│       │   ├── repository.py
│       │   ├── service.py
│       │   └── routes.py
│       ├── assistant/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── interface.py
│       │   ├── demo.py
│       │   ├── gemini.py
│       │   ├── repository.py
│       │   ├── service.py
│       │   └── routes.py
│       ├── templates/
│       │   ├── base.html
│       │   ├── partials/
│       │   │   └── sidebar.html
│       │   ├── dashboard.html
│       │   ├── assignments/
│       │   │   ├── index.html
│       │   │   └── editor.html
│       │   └── assistant/
│       │       ├── index.html
│       │       └── artifact.html
│       ├── static/
│       │   ├── css/
│       │   │   ├── input.css
│       │   │   └── app.css
│       │   └── js/
│       │       └── assistant.js
│       └── scripts/
│           ├── seed_demo.py
│           └── gemini_smoke_test.py
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

Files must remain focused.

Do not create large utility files containing unrelated functionality.

---

## Development Process

For every task:

1. Read `AGENTS.md` completely.
2. Inspect the current repository before changing files.
3. Inspect relevant models, routes, services, repositories, templates, tests, migrations, and recent commits.
4. Work only on the active task.
5. Do not begin later tasks.
6. Write or update focused tests before implementation.
7. Run the focused tests.
8. Confirm they fail for the expected reason.
9. Implement the minimum required behavior.
10. Run the focused tests again.
11. Run the complete test suite.
12. Run Ruff lint checks.
13. Run Ruff formatting checks.
14. Build Tailwind CSS when templates or Tailwind classes change.
15. Run required Alembic migrations when the database schema changes.
16. Do not disable, skip, or weaken existing tests.
17. Do not hide failures.
18. Do not perform unrelated refactoring.
19. Preserve existing working behavior unless the active task explicitly changes it.
20. Stop after completing the active task.

Use test-driven development.

Do not claim completion unless verification commands actually pass.

---

## Required Verification

Unless the active task specifies additional commands, run:

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

When the database schema changes, also run:

```bash
uv run alembic upgrade head
```

When Tailwind classes or templates change, build the stylesheet:

```bash
.tools/tailwindcss \
  -i ./src/greader/static/css/input.css \
  -o ./src/greader/static/css/app.css
```

When manually running the application:

```bash
uv run uvicorn greader.main:app --reload
```

Automated tests must use:

```text
AI_PROVIDER=demo
```

unless a fake provider is explicitly injected.

Real Gemini API calls are allowed only in an explicit manual smoke test.

---

## Task Scope

Task-specific instructions from the current user prompt define the active scope.

Complete only the active task.

Do not implement future requirements merely because they are described in this file.

Do not add authentication, student features, code execution, analytics, mutation testing, GitHub integration, or deployment unless the active task explicitly requests them.

For the current presentation MVP, stop after completing the AI generation, preview, and save workflow.

---

## End-of-Task Report

At the end of every task, report:

- Files created.
- Files modified.
- Dependencies added or removed.
- Database migrations created.
- Commands executed.
- Focused test results.
- Complete test results.
- Ruff lint result.
- Ruff format result.
- Tailwind build result when applicable.
- Manual smoke-test result when applicable.
- Exact behavior now supported.
- Remaining limitations.
- Suggested commit message.

Do not claim a test, migration, build, or manual verification passed unless it was actually executed successfully.

---

## Explicitly Postponed Features

Do not implement these during the current MVP unless a later task explicitly requests them:

- Instructor authentication.
- Student accounts.
- Student submissions.
- Running reference solutions.
- Executing student code.
- Docker judge sandbox.
- Hidden judge test cases.
- Mutation testing against executable code.
- Difficulty prediction from real submission data.
- Assignment analytics.
- GitHub integration.
- GitHub Classroom integration.
- WebSocket streaming.
- Celery.
- Redis.
- Voice recording.
- Multiple programming languages.
- Plagiarism detection.
- Usage billing.
- Production deployment.
- AI-generated content auto-publishing.
