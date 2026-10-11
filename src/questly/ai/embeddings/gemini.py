"""Gemini text embedding adapter; the SDK client is supplied by the caller.

Production composition creates ``google.genai.Client`` after credentials are
configured. Importing this module never reads credentials or contacts Google.
"""

import os
from math import hypot, isfinite
from typing import Protocol

from dotenv import load_dotenv

from questly.ai.app.models import EMBEDDING_DIMENSION, Embedding
from questly.ai.embeddings.ports import EmbeddingError

MODEL = "gemini-embedding-001"


class _Embedding(Protocol):
    values: list[float] | None


class _Response(Protocol):
    embeddings: list[_Embedding] | None


class _Models(Protocol):
    def embed_content(
        self, *, model: str, contents: str, config: dict[str, object]
    ) -> _Response: ...


class GeminiClient(Protocol):
    models: _Models


class GeminiEmbeddingProvider:
    """Request 768 dimensions and L2-normalize the truncated 001 output."""

    def __init__(self, client: GeminiClient) -> None:
        self._client = client

    @property
    def model(self) -> str:
        return MODEL

    def embed(self, text: str) -> Embedding:
        if not text.strip():
            raise EmbeddingError("cannot embed empty text")
        response = self._client.models.embed_content(
            model=MODEL,
            contents=text,
            config={
                "output_dimensionality": EMBEDDING_DIMENSION,
                "task_type": "RETRIEVAL_DOCUMENT",
            },
        )
        embeddings = response.embeddings
        if embeddings is None or len(embeddings) != 1:
            raise EmbeddingError("provider must return one embedding")
        values = embeddings[0].values
        if values is None or len(values) != EMBEDDING_DIMENSION:
            raise EmbeddingError("provider returned the wrong embedding dimension")
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EmbeddingError("provider returned non-numeric values")
            try:
                finite = isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise EmbeddingError("provider returned non-finite values")
        try:
            magnitude = hypot(*values)
        except OverflowError as exc:
            raise EmbeddingError("provider returned an invalid vector") from exc
        if not isfinite(magnitude) or magnitude == 0:
            raise EmbeddingError("provider returned a zero or invalid vector")
        return tuple(value / magnitude for value in values)


def create_gemini_embedding_provider(api_key: str) -> GeminiEmbeddingProvider:
    """Construct the production adapter only when explicitly configured."""
    if not api_key.strip():
        raise ValueError("Gemini API key is required")
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai dependency is required") from exc
    return GeminiEmbeddingProvider(genai.Client(api_key=api_key))


def create_gemini_embedding_provider_from_env() -> GeminiEmbeddingProvider:
    """Load local configuration only when the production adapter is requested."""
    load_dotenv(override=False)
    return create_gemini_embedding_provider(os.environ.get("GEMINI_API_KEY", ""))
