"""OpenRouter text embedding adapter for the existing 768-dimensional RAG schema.

The client is injected for tests. Constructing a production client happens only
when the factory is called, so imports remain credential- and network-free.
"""

import os
from math import hypot, isfinite
from typing import Protocol

from dotenv import load_dotenv

from questly.ai.app.models import EMBEDDING_DIMENSION, Embedding
from questly.ai.embeddings.ports import EmbeddingError

MODEL = "google/gemini-embedding-001"
BASE_URL = "https://openrouter.ai/api/v1"


class _Embedding(Protocol):
    embedding: list[float]


class _Response(Protocol):
    data: list[_Embedding]


class _Embeddings(Protocol):
    def create(
        self,
        *,
        model: str,
        input: str,
        dimensions: int,
        encoding_format: str,
    ) -> _Response: ...


class OpenRouterClient(Protocol):
    embeddings: _Embeddings


class OpenRouterEmbeddingProvider:
    """Request 768 dimensions and L2-normalize the returned vector."""

    def __init__(self, client: OpenRouterClient) -> None:
        self._client = client

    @property
    def model(self) -> str:
        return MODEL

    def embed(self, text: str) -> Embedding:
        if not text.strip():
            raise EmbeddingError("cannot embed empty text")
        response = self._client.embeddings.create(
            model=MODEL,
            input=text,
            dimensions=EMBEDDING_DIMENSION,
            encoding_format="float",
        )
        data = response.data
        if data is None or len(data) != 1:
            raise EmbeddingError("provider must return one embedding")
        values = data[0].embedding
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


def create_openrouter_embedding_provider(api_key: str) -> OpenRouterEmbeddingProvider:
    """Construct the production adapter only when explicitly configured."""
    if not api_key.strip():
        raise ValueError("OpenRouter API key is required")
    return OpenRouterEmbeddingProvider(_new_client(api_key))


def _new_client(api_key: str) -> OpenRouterClient:
    from openai import OpenAI

    return OpenAI(base_url=BASE_URL, api_key=api_key, timeout=60.0)


def create_openrouter_embedding_provider_from_env() -> OpenRouterEmbeddingProvider:
    """Load local configuration only when the production adapter is requested."""
    load_dotenv(override=False)
    return create_openrouter_embedding_provider(
        os.environ.get("OPENROUTER_API_KEY", "")
    )
