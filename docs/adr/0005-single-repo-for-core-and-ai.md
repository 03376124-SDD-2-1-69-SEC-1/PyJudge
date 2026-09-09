# Single repo for Core and AI

The original plan split Core and the AI/RAG service into two repositories,
sharing `core/generation/schemas.py` by keeping a byte-for-byte copy in each
(CORE-01's original done-condition). That plan was abandoned in practice
before it was abandoned on paper: AI-01 landed AI code under
`src/greader/ai/` in this repo, and `docs/task-scope.md` kept describing an
"ai repo" that never existed. This ADR makes the single repo the deliberate
choice instead of an unreviewed fact, and OPS-08 rewrites `task-scope.md` and
`AGENTS.md` to match it. Consequence: `core` and `ai` share one dependency
set, one test suite, and one Alembic history (already the case per
[0004](0004-single-alembic-history-for-both-schemas.md)); the import
direction stays one-way — `ai` may import `core`, `core` must never import
`ai` — and the generation contract in `core/generation/schemas.py` is now a
single file both sides import, not two files kept in sync by hand.
