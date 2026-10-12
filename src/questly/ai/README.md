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

Production embedding uses `OpenRouterEmbeddingProvider`, which calls
`embeddings.generate` on the `openrouter` SDK (ADR-0009) with
`dimensions=768` and L2-normalizes the result. Build it with
`create_openrouter_embedding_provider(settings.openrouter_api_key,
settings.embedding_model)`; `EMBEDDING_MODEL` defaults to
`google/gemini-embedding-001`. Changing the model means re-embedding every
chunk, and the replacement must return 768 dimensions. SDK failures, including
timeouts, surface as `EmbeddingError`. Imports and tests never load
credentials or contact an AI provider.

This module does not fetch objects from R2, perform OCR, or ingest the seed
corpus. Those are later tasks. No tests may call shared Neon, real R2, or a
real embedding provider; use the dedicated throwaway infrastructure instead.
