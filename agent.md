You are building a web application named GReader.

GReader is an instructor-first, AI-assisted programming assignment authoring platform for university instructors.

The system helps instructors:

Write programming assignment descriptions.
Define constraints and difficulty.
Add a reference solution.
Generate candidate test cases.
Review, approve, reject, and edit test cases.
Detect missing edge cases and ambiguous requirements.
Simulate assignment validation.
Measure assignment quality before publishing.

This is not a student-focused online judge and must not look like LeetCode.

Technology constraints

Use only the following core stack:

Python 3.12
uv for project and dependency management
FastAPI
Jinja2 server-rendered HTML templates
Tailwind CSS
Tailwind standalone CLI without Node.js or npm
Minimal vanilla JavaScript only when server-rendered HTML cannot provide the interaction
pytest
FastAPI TestClient
Playwright Python for E2E testing

Do not use:

React
Vue
Next.js
Vite
npm
Node.js
TypeScript
A frontend SPA
Supabase
External authentication services
Real LLM APIs during the initial demo
Arbitrary Python code execution during the initial demo
Architecture rules

Use a modular FastAPI monolith.

Keep business logic separate from HTTP routes and templates.

Use an application factory:

def create_app(...) -> FastAPI:
    ...

Expose an application instance for Uvicorn:

app = create_app()

Use dependency injection or app.state for repositories and services so tests can create isolated application instances.

Use paths relative to the installed Python package, not the current working directory, when locating templates and static files.

Suggested structure:

greader/
├── pyproject.toml
├── uv.lock
├── README.md
├── .python-version
├── .gitignore
├── .tools/
│   └── tailwindcss
├── src/
│   └── greader/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── web/
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   └── dependencies.py
│       ├── assignments/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── repository.py
│       │   ├── service.py
│       │   └── routes.py
│       ├── assistant/
│       │   ├── __init__.py
│       │   ├── interface.py
│       │   └── demo.py
│       ├── templates/
│       │   ├── base.html
│       │   ├── partials/
│       │   │   └── sidebar.html
│       │   ├── dashboard.html
│       │   └── assignments/
│       │       ├── index.html
│       │       └── editor.html
│       └── static/
│           └── css/
│               ├── input.css
│               └── app.css
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
Development rules

For every task:

Inspect the current repository before changing files.
Work only on the requested task.
Do not start later tasks.
Write or update tests before implementing behavior.
Run the focused tests and confirm they fail for the expected reason.
Implement the minimum code required.
Run all tests.
Run Ruff checks and formatting checks.
Do not hide failures or disable tests.
Do not add dependencies unless the current task requires them.
Do not perform unrelated refactoring.
Keep functions and files focused.
Preserve server-rendered HTML.
Prefer normal HTML links and forms over client-side state.
Use POST-Redirect-GET for form mutations.

At the end of every task, report:

Files created.
Files modified.
Commands executed.
Test results.
Remaining limitations.
Suggested commit message.

Do not claim completion unless the verification commands actually pass.
Task-specific instructions from the current user prompt define the active scope.
Complete only the active task and do not implement future tasks, even when their requirements are known.
## AI Authoring Phase

GReader now includes an instructor-facing AI authoring workflow.

Permanent constraints:

- The application remains a Python-only modular FastAPI monolith.
- Frontend pages use Jinja2, Tailwind CSS, and minimal vanilla JavaScript.
- Do not introduce React, Vue, Node.js, npm, PocketBase, MongoDB, or a frontend SPA.
- Use synchronous SQLAlchemy 2.x sessions for the initial implementation.
- Use SQLite during local development and tests.
- Keep the database configuration compatible with PostgreSQL through `DATABASE_URL`.
- Use Alembic for every database schema change.
- AI-generated data must be validated with Pydantic before entering the domain layer.
- AI-generated assignments and test cases are drafts until an instructor explicitly applies them.
- Never automatically publish AI-generated content.
- Never execute AI-generated Python code during this phase.
- Never send API keys, system prompts, or internal errors to the browser.
- Automated tests must never make real AI network requests.
- Keep the AI provider behind an interface so the demo provider and Gemini provider are replaceable.
- Version 1 supports Python stdin/stdout programming assignments only.
- A reference solution is a complete Python program that reads stdin and writes stdout.
- A test case contains plain-text input and its expected plain-text output.
- Complete only the active task. Do not implement requirements from later tasks.
Shared instruction for every task

Place this before each individual task prompt:

Read `AGENTS.md` completely before making changes.

Inspect the repository, current models, routes, templates, tests, and recent commits before deciding where code belongs.

Execute only the task below. Do not begin any later task.

Use test-driven development:

1. Write or update focused tests first.
2. Run them and confirm they fail for the expected reason.
3. Implement the minimum required behavior.
4. Run focused tests.
5. Run the full test suite.
6. Run Ruff checks and formatting checks.
7. Do not disable, skip, or weaken existing tests.

Preserve existing working behavior and repository interfaces unless this task explicitly changes them.

At the end, report:

- files created
- files modified
- database migrations created
- commands executed
- focused test results
- complete test results
- lint and format results
- remaining limitations
- suggested commit message