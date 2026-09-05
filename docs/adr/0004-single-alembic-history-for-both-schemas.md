# Single Alembic history for both schemas

One Alembic history, in this repo, covers both the `core` and `rag` Postgres
schemas — migrations are not split per service. The Core and RAG/AI services
talk over HTTP with no cross-schema foreign key, so a split history per
service would mirror that boundary, but with a single-node deployment and a
two-person team the extra coordination overhead of two Alembic histories
(two `alembic_version` tables, two release sequences to keep straight) is not
worth it yet. `env.py` sets `include_schemas=True` so Alembic sees objects in
both schemas, and `database/__init__.py` must keep importing both
`core.tables` and `rag.tables` — autogenerate silently skips any table
module that isn't imported. If the AI service is ever split into its own
repo, the `rag` revisions must be extracted into their own history at that
point; until then they stay interleaved with `core` revisions in
`alembic/versions/`.
