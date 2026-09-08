# Task scope

Maps a TASK-ID to who owns it, which paths it may touch, and what "done" means.
Read by `/grill-me`. Keep in sync with the team board.

This is a single repo. "ai repo" in this table resolves to `src/greader/ai/`.

| TASK-ID | Owner | May touch | Done when |
|---|---|---|---|
| OPS-* | พาย | anything | varies, see board |
| CORE-01 | พาย + ฟิล์ม | `src/greader/core/generation/schemas.py` | `core/generation/schemas.py` exists once in this repo. Done — merged in PR #3 |
| CORE-02 | พาย | `core/generation/routes.py`, `ai/client.py` | mock endpoint callable from outside. Done — merged in PR #4 |
| CORE-03 | พาย | `core/topics/`, `tests/` | merged to dev and runs |
| CORE-04 | นัด | `core/assignments/`, `database/core/assignment_repository.py`, `tests/` | create, update, delete via API |
| CORE-05 | นัด | `core/test_cases/`, `database/core/test_case_repository.py`, `tests/` | linked to an assignment, deleted with it |
| CORE-06 | พาย | `database/storage.py`, config | file uploads to R2 through an endpoint |
| CORE-07 | นัด + โปรแกรม | `core/assignments/`, `web/templates/`, `core/assignments/routes.py` | assignment saved from an approved draft |
| FE-01 | โปรแกรม | `web/templates/base.html`, `web/static/css/input.css` | every page extends base |
| FE-02 | โปรแกรม | `web/templates/generate.html`, `core/generation/routes.py` | submit renders a draft from the mock |
| FE-03 | โปรแกรม | `web/templates/review.html`, `core/assignments/routes.py` | citations shown, approve and reject work |
| FE-04 | โปรแกรม | `web/templates/save.html`, `core/assignments/routes.py` | form matches the mockup |
| AI-01 | ฟิล์ม | ai repo: `app/`, `database/`; `tests/unit/ai/`; AI-01-specific files under `tests/integration/`, `tests/architecture/`; this AI-01 clarification in `docs/task-scope.md` | insert and query a sample vector |
| AI-02 | ฟิล์ม | ai repo: `ingestion/` | text extracted per page from the test files |
| AI-03 | พาย + ฟิล์ม | ai repo: `ingestion/chunking.py` | chunk boundaries match expectations on >=80% of test files |
| AI-04 | ฟิล์ม | ai repo: `ingestion/`, `embeddings/` | one PDF ingested end to end, chunks and vectors present |
| AI-05 | ฟิล์ม | ai repo: `retrieval/` | filtered query returns source_id, page, score |
| AI-06 | พาย | ai repo: `generation/` | draft and citations returned per the contract |
| AI-07 | ฟิล์ม | ai repo: `routes/knowledge.py` | deleting a document leaves no chunks behind |
| DES-02 | อุ้ม | ai repo: `tests/fixtures/pdfs/`, `docs/` | files present with a digital/scan table |
| DES-03 | อุ้ม | `docs/test-scenarios.md` | a checklist someone can follow |
| BUG-* | varies | whatever the fix needs, nothing more | the failing scenario passes |
| OPS-08 | พาย | `docs/task-scope.md`, `AGENTS.md`, `docs/adr/`, `.gitignore` | the table matches the tree; every done-condition is checkable in one repo |
| CORE-08 | พาย + ฟิล์ม | `core/generation/schemas.py`, `ai/client.py`, `tests/unit/ai/test_client.py`, `tests/integration/test_generation_api.py` | a citation identifies its source document; an approved draft has a stable handle; invalid input is rejected |
| CORE-09 | พาย | `core/knowledge_documents/`, `database/core/knowledge_document_repository.py`, `tests/` | a citation's `document_id` resolves to the document's filename through Core |

AI-01 database adapters may live under `src/greader/ai/database/` and reuse the
ORM tables from `src/greader/database/rag/tables.py`.

## AI-01 runbook (Film)

Automated tests validate domain/service/application behavior and mocked
PostgreSQL adapter behavior. Real PostgreSQL insertion, pgvector querying,
transaction rollback, and cleanup remain unverified until the separate manual
smoke check is run. Task 5 does not run that check or contact shared Neon.

### Start the standalone AI application

From the repository root, provide `DATABASE_URL` through the process environment
using the team's approved secret mechanism. It must use `postgresql+psycopg://`.
The factory does not load `.env`; it creates the engine without connecting until
an operation needs it. Do not print credentials or put them in shell history.

```powershell
rtk proxy uv run uvicorn greader.ai.app.main:create_production_app --factory --host 127.0.0.1 --port 8001
```

Local API documentation: <http://127.0.0.1:8001/docs>.
Core remains a separate HTTP application. Tests instead call
`create_app(repository=InMemoryVectorRepository())` without credentials.

### Manual PostgreSQL smoke check (separate, authorized session only)

Use an approved PostgreSQL target with the existing schema and pgvector already
installed. Never run migrations for this check. The following PowerShell block
uses only Python's standard library for HTTP and deterministic 768-value vectors:
`[1, 0, ...]` and `[0, 1, 0, ...]`. It writes one source with two tied vectors,
one orthogonal vector, and one NULL embedding. No R2 object or Core record is
created. Use a unique marker and a positive synthetic BIGINT; on a source-ID
conflict, generate a fresh run instead of changing or deleting existing data.

```powershell
@'
import json
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base = "http://127.0.0.1:8001/api/v1"
marker = "ai01-smoke-" + uuid.uuid4().hex
document_id = uuid.uuid4().int % (2**63 - 1) + 1
vector = [1.0] + [0.0] * 767
orthogonal = [0.0, 1.0] + [0.0] * 766

def post(path, body, expected):
    request = Request(base + path, json.dumps(body).encode(),
                      {"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            status, data = response.status, json.load(response)
    except HTTPError as error:
        status, data = error.code, json.load(error)
    assert status == expected, (status, data)
    return data

payload = {
    "core_document_id": document_id,
    "r2_object_key": marker,
    "content_hash": marker,
    "embedding_model": marker,
    "embedding_dim": 768,
    "metadata": {"ai01_smoke": marker},
    "chunks": [
        {"chunk_index": i, "page": i + 1, "text": "smoke " + str(i),
         "content_hash": marker + "-" + str(i), "embedding_model": marker,
         "metadata": {"ai01_smoke": marker}, "embedding": embedding}
        for i, embedding in enumerate([vector, vector, orthogonal, None])
    ],
}
# Save this marker even if a later request fails or times out.
print("MARKER:", marker, "CORE_DOCUMENT_ID:", document_id, flush=True)
created = post("/knowledge-sources", payload, 201)
source_id = created["source"]["id"]
print("SOURCE_ID:", source_id, flush=True)
query = {"embedding": vector, "embedding_model": marker, "top_k": 10}
matches = post("/knowledge-chunks/search", query, 200)
assert [m["chunk_id"] for m in matches] == [c["id"] for c in created["chunks"][:3]]
assert all(abs(m["score"] - score) < 1e-6
           for m, score in zip(matches, [1.0, 1.0, 0.0], strict=True))
assert post("/knowledge-chunks/search", dict(query, embedding_model=marker + "-other"), 200) == []
assert post("/knowledge-sources", payload, 409)["detail"]["code"] == "duplicate_knowledge_source"

# Force a chunk uniqueness failure after a new source insert.
rollback_id = uuid.uuid4().int % (2**63 - 1) + 1
print("ROLLBACK_CORE_DOCUMENT_ID:", rollback_id, flush=True)
failed = dict(payload, core_document_id=rollback_id,
              chunks=[payload["chunks"][0], payload["chunks"][0]])
assert post("/knowledge-sources", failed, 409)["detail"]["code"] == "duplicate_knowledge_chunk"
print("HTTP checks passed; verify rows and cleanup below.")
'@ | rtk proxy uv run python -
```

Creation returns integer source/chunk IDs and omits embeddings. Search returns
`chunk_id`, `source_id`, `page`, `text`, and `score = 1 - cosine distance`, ordered
by descending score then ascending chunk ID. Model matching is exact; NULL
embeddings are excluded. Invalid vectors (including zero vectors) return 422;
`top_k` must be 1–100. Duplicate source/chunk conflicts return 409; unavailable
storage returns a sanitized 503. Unexpected storage errors return 500.

In an approved SQL console, replace the four placeholders below with the exact
printed values. First inspect the tagged source and its four chunks. Verify no
source exists for `ROLLBACK_CORE_DOCUMENT_ID`; that checks the real transaction
rollback. If a request timed out, locate records by the exact marker and original
Core document ID before deciding whether to retry or clean up.

```sql
SELECT id, core_document_id, r2_object_key, metadata
FROM rag.knowledge_sources
WHERE metadata->>'ai01_smoke' = 'MARKER';
SELECT id, source_id, embedding IS NULL AS null_embedding
FROM rag.knowledge_chunks WHERE source_id = SOURCE_ID ORDER BY id;
SELECT id FROM rag.knowledge_sources
WHERE core_document_id = ROLLBACK_CORE_DOCUMENT_ID;

BEGIN;
DELETE FROM rag.knowledge_sources
WHERE id = SOURCE_ID
  AND core_document_id = CORE_DOCUMENT_ID
  AND r2_object_key = 'MARKER'
  AND metadata->>'ai01_smoke' = 'MARKER'
RETURNING id;
-- Expect exactly the inspected source; its chunks use ON DELETE CASCADE.
SELECT id FROM rag.knowledge_chunks WHERE source_id = SOURCE_ID;
-- Expect zero chunks. COMMIT only after both results match; otherwise ROLLBACK.
COMMIT;
```

After commit, repeat the marker/source queries and the same model search; expect
no rows and `[]`. If rollback verification unexpectedly finds a source, inspect
it and use its exact ID, Core document ID, and marker in the same guarded cleanup.
Never delete by prefix, truncate tables, or delete unrelated shared data. Never
paste credentials into reports. Record target alias, marker, IDs, outcomes, and
cleanup confirmation without the DSN.

Limitations: mocked tests cannot establish database durability or rollback.
PostgreSQL stores pgvector components at single precision; in-memory arithmetic
uses Python floats, so close scores can differ. Use these unit-axis vectors for
reproducible smoke checks. No delete endpoint, ingestion, or embedding provider is
part of AI-01. A connection failure around commit can leave the outcome unknown;
inspect tagged records before retrying.

## Off-limits regardless of task

Only an OPS task, assigned to พาย, may change:

- `alembic/` and anything that runs a migration
- `.env`, `.env.example`, credentials
- `database/core/tables.py`, `database/rag/tables.py`
- `pyproject.toml` dependencies
- CI config, `.gitignore`
