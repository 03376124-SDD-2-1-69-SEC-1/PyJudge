---
status: accepted
date: 2026-10-12
task: OPS-23
---

# OpenRouter is the only AI provider, called through the `openrouter` SDK

## Context

By October 2026 the repo named three AI providers at once. Generation (AI-06)
called OpenRouter through the `openai` SDK pointed at OpenRouter's
OpenAI-compatible endpoint. Embeddings (AI-04) did the same. The
`core.ai_settings` seed from ADR-0008 said provider `gemini`, CI set
`GEMINI_API_KEY` and `GEMINI_MODEL` that nothing read, and the AI-04 row in
`docs/task-scope.md` still offered `google-genai` or `sentence-transformers`.

## Decision

OpenRouter is the single provider for generation and for embeddings. Both call
it through the official `openrouter` Python SDK: `chat.send` in
`ai/client.py`, `embeddings.generate` in `ai/embeddings/openrouter.py`. The
`openai` dependency is removed and `google-genai` is never added.

Configuration lives in `Settings`. `OPENROUTER_API_KEY` is the one key; an
empty key wires `StubGenerationClient`. `GENERATION_MODEL` defaults to
`DEFAULT_GENERATION_MODEL` in `config.py`. `EMBEDDING_MODEL` defaults to
`google/gemini-embedding-001`, the model every stored vector was made with.
Changing it means re-embedding every chunk, and the replacement must return
768 dimensions to fit `VECTOR(768)`.

This supersedes the `gemini` seed in ADR-0008. A hand-written, data-only
revision after `c4e8a2f17b90` sets the `core.ai_settings` row to provider
`openrouter` and model `DEFAULT_GENERATION_MODEL`; its downgrade restores the
old values.

## Why

- One key and one bill cover both uses, and any model on OpenRouter is one
  setting away.
- The official SDK types OpenRouter's own API, errors and retries, instead of
  relying on how closely the endpoint follows OpenAI's.
- A CI secret nothing reads and a seed naming a provider no code calls
  mislead the next reader.

## Consequences

- `openrouter` 1.3.43 pins `pydantic<2.13`, so uv moved pydantic from 2.13.4
  to 2.12.5 on its own. The full suite passed after the downgrade (636 tests
  at the commit that made the swap).
- The SDK retries until a time budget runs out, not a fixed count. Left
  unset, it retries 5XX and connection errors for up to an hour, and
  `chat.send` does not retry 429. Both adapters therefore pass their own
  `RetryConfig` with a short budget that includes 429.
- The SDK raises `NoResponseError` outside `OpenRouterError`, and once
  retries are spent it lets `httpx` timeout and network errors through
  unwrapped. Both adapters catch all three: generation logs and re-raises,
  embeddings wrap them in `EmbeddingError`.
