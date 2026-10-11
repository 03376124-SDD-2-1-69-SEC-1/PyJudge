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

Production embedding uses `GeminiEmbeddingProvider` with
`gemini-embedding-001`, 768 output dimensions, and manual L2 normalization.
Pass an SDK client explicitly, call `create_gemini_embedding_provider` with
an explicit API key, or call `create_gemini_embedding_provider_from_env` to
load `GEMINI_API_KEY` from the local environment at runtime. Imports and tests
never load credentials or contact Google.
The `google-genai` dependency must be added by the OPS owner to
`pyproject.toml` and `uv.lock` before production composition can instantiate it.

This module does not fetch objects from R2, perform OCR, or ingest the seed
corpus. Those are later tasks. No tests may call shared Neon, real R2, or a
real embedding provider; use the dedicated throwaway infrastructure instead.
