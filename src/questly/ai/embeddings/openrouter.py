"""OpenRouter text embedding adapter for the existing 768-dimensional RAG schema.

Calls OpenRouter through the `openrouter` SDK (ADR-0009). The client is injected
for tests, and the model name comes from `Settings.embedding_model`.
"""

from math import hypot, isfinite
from typing import Protocol

import httpx
from openrouter import OpenRouter
from openrouter.errors import NoResponseError, OpenRouterError
from openrouter.utils.retries import BackoffStrategy, RetryConfig

from questly.ai.app.models import EMBEDDING_DIMENSION, Embedding
from questly.ai.embeddings.ports import EmbeddingError

_TIMEOUT_MS = 60_000
# Left unset, the SDK retries 5XX and connection errors for up to an hour.
# A 5s budget gives two or three retries, close to the openai client's two.
_RETRY = RetryConfig(
    "backoff",
    BackoffStrategy(
        initial_interval=500, max_interval=8_000, exponent=2, max_elapsed_time=5_000
    ),
    retry_connection_errors=True,
    status_codes_override=["429", "5XX"],
)
# The SDK raises NoResponseError outside OpenRouterError, and lets httpx's
# timeout and network errors through unwrapped once retries are spent.
_SDK_ERRORS = (OpenRouterError, NoResponseError, httpx.TransportError)


class _Embedding(Protocol):
    embedding: list[float]


class _Response(Protocol):
    data: list[_Embedding]


class _Embeddings(Protocol):
    def generate(
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

    def __init__(self, client: OpenRouterClient, model: str) -> None:
        self._client = client
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def embed(self, text: str) -> Embedding:
        if not text.strip():
            raise EmbeddingError("cannot embed empty text")
        try:
            response = self._client.embeddings.generate(
                model=self._model,
                input=text,
                dimensions=EMBEDDING_DIMENSION,
                encoding_format="float",
            )
        except _SDK_ERRORS as exc:
            raise EmbeddingError(f"OpenRouter embedding call failed: {exc}") from exc
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


def create_openrouter_embedding_provider(
    api_key: str, model: str
) -> OpenRouterEmbeddingProvider:
    """Construct the production adapter from `Settings`."""
    if not api_key.strip():
        raise ValueError("OpenRouter API key is required")
    return OpenRouterEmbeddingProvider(_new_client(api_key), model)


def _new_client(api_key: str) -> OpenRouterClient:
    return OpenRouter(api_key=api_key, timeout_ms=_TIMEOUT_MS, retry_config=_RETRY)
