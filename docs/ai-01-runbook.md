# AI-01 vector storage runbook

## Application and infrastructure

Vector endpoints are part of the main FastAPI application:

- `POST /api/v1/knowledge-sources`
- `POST /api/v1/knowledge-chunks/search`

Start the production composition from the repository root:

```powershell
rtk proxy uv run uvicorn greader.main:app --host 127.0.0.1 --port 8000
```

The equivalent factory entry point is `greader.main:create_production_app` with
`--factory`. Both select `PostgresVectorRepository`; neither falls back to
in-memory persistence when production configuration is missing. Open `/docs`
on this same application to inspect both vector endpoints and the Core APIs.
Core services do not import AI services or access RAG tables directly.

Database and R2 initialization is deferred until the corresponding dependency
is requested. The existing `.env` loading behavior is retained at that point.
`DATABASE_URL` must use `postgresql+psycopg://`. R2 retains `R2_ENDPOINT_URL`,
`R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY`, with the same
signature version, region, bucket, and object-key behavior. Missing configuration
raises a clear error naming the required setting. Never paste credentials into
commands or reports.

Tests use `create_app(vector_repository=InMemoryVectorRepository())`, or supply a
repository backed by OPS-09's isolated database. Importing `greader.main` and
constructing either app factory does not construct DB/R2 clients or connect to
external services. Infrastructure health checks retain their dependency override
seams. Factories cache successfully initialized infrastructure for the process;
restart the process after changing configuration.

## API behavior

Creation requires at least one chunk. Empty chunks return 422 without consuming
the document ID. The service also enforces this rule outside HTTP. A client-sent
`status` is ignored; new sources start as `pending`. Responses retain `status`,
integer IDs, and chunk input order, and omit embeddings.

Creation uses one source INSERT and one multi-VALUES chunk INSERT in a single
transaction. Returned chunks are matched by their source-scoped unique content
hash, so response order does not depend on SQL RETURNING order. Duplicate source
and chunk constraints produce 409 with `duplicate_knowledge_source` and
`duplicate_knowledge_chunk`, respectively, and creation is rolled back.

Search requires a nonzero, finite 768-component vector, an exact embedding model,
and `top_k` from 1 through 100. NULL embeddings and other models are excluded.
Results contain `chunk_id`, `source_id`, `page`, `text`, and `score`. SQL orders
by cosine distance ascending, then chunk ID ascending. The adapter calculates
`score = 1 - distance`; clients receive descending similarity with stable ID ties.
The query uses the distance operator directly rather than sorting a derived score.
Compiled SQL tests do not prove that PostgreSQL chooses the HNSW index.

All 422 responses use `{"detail": {"code": "...", "message": "..."}}`.
Pydantic request failures use `request_validation_error`; service validation uses
`vector_validation_error`. The global handler covers Core endpoints too and does
not echo submitted values. Existing non-validation error codes remain unchanged.
Unavailable vector storage returns a sanitized 503. Unexpected exceptions remain
500 errors rather than being mislabeled as unavailable storage.

## Validation

Run the standard checks after every review item:

```powershell
rtk proxy uv run pytest
rtk proxy uv run ruff check .
rtk proxy uv run ruff format --check .
```

On Windows, existing template architecture tests need `PYTHONUTF8=1`. Existing
upload tests need a nonempty dummy `R2_BUCKET_NAME` even though they override the
client. These may be set only in the test process; no credential file changes are
needed. AI-01's fresh-process regression test removes DB/R2 credentials, disables
dotenv loading, and rejects engine/client construction and socket connections.

Focused suites:

```powershell
rtk proxy uv run pytest tests/unit/ai tests/integration/test_ai_vector_api.py tests/integration/test_ai_validation_errors.py tests/architecture/test_ai_vector_boundaries.py
rtk proxy uv run pytest tests/db/test_vector_repository_postgres.py -rs
```

The four AI-01 database tests use the `postgres` marker and receive their DSN only
from OPS-09's `postgres_url` fixture. They exercise HTTP through ASGITransport,
the service, the PostgreSQL adapter, and the real database when configured:

1. Source/chunk insertion, input-order preservation, and search round trip.
2. Cosine ranking, ID ties, and NULL embedding exclusion using unit vectors.
3. Duplicate chunk conflict and source rollback verified from a separate
   connection, followed by a successful retry for the same document ID.
4. An unrelated embedding model returning an empty result list.

Each test uses unique data and deletes only its exact marked source afterward;
the existing foreign key cascades chunk cleanup. Tests never run migrations.

Without `POSTGRES_TEST_URL`, these tests and OPS-09's canary skip locally. CI
supplies the isolated database and must report `tests/db/` as executed, not
skipped. Do not use the team's shared Neon branch, run a shared-Neon smoke check,
or substitute `DATABASE_URL` for the test fixture. Review CI results for the
final pushed commit after the owner approves the local diff.

## Limits

In-memory and mocked session tests do not prove PostgreSQL persistence, rollback,
or index use. Local skips leave real PostgreSQL execution pending CI. pgvector
stores single-precision components while the in-memory implementation uses
Python floats, so close scores may differ. No ingestion, embedding provider, or
delete endpoint is included. A connection failure around commit can leave its
outcome unknown; inspect the exact source identity before retrying.
