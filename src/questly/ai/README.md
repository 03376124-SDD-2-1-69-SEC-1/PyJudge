# AI module

AI-01 persists knowledge sources and pgvector chunks through `VectorService`.
AI-02 extracts every physical PDF page, and AI-03 splits one statement at the
Thai input heading. AI-04 connects those parts in `ingestion/pipeline.py`:

1. Pass PDF bytes, a `core_document_id`, and its existing R2 object key to
   `PdfIngestionService.ingest`.
2. The service rejects pages requiring OCR and documents without usable text.
3. It embeds every chunk before asking `VectorService` to persist the source
   and chunks atomically with status `ready`.
4. Each chunk stores its starting page in `page` and its inclusive ending page
   in metadata `page_end`; source metadata such as topic/difficulty is retained.

Production embedding uses `OpenRouterEmbeddingProvider` with
`google/gemini-embedding-001` through OpenRouter's OpenAI-compatible embedding
endpoint, requesting 768 output dimensions and applying L2 normalization.
Pass an OpenAI-compatible client explicitly, call
`create_openrouter_embedding_provider` with an explicit key, or call
`create_openrouter_embedding_provider_from_env` to load `OPENROUTER_API_KEY`
at runtime. The existing `openai` dependency is sufficient. Imports and tests
never load credentials or contact an AI provider.

AI-04 scope note for PR review: `docs/task-scope.md` still names the direct
`google-genai` SDK (or `sentence-transformers`) and asks the OPS owner to add
it. Pai approved OpenRouter instead; this implementation reuses the existing
`openai` dependency and OpenRouter key, without touching locked dependency or
scope files. The scope row should be updated by its owner when convenient.

This module does not fetch objects from R2, perform OCR, or ingest the seed
corpus. Those are later tasks. No tests may call shared Neon, real R2, or a
real embedding provider; use the dedicated throwaway infrastructure instead.
