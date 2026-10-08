"""Provider-independent text embedding contract."""

from typing import Protocol

from questly.ai.app.models import Embedding


class EmbeddingError(Exception):
    """A provider did not return a usable embedding."""


class EmbeddingProvider(Protocol):
    """Embed one document chunk with a stable model identity."""

    @property
    def model(self) -> str:
        """Return the exact model name stored with each vector."""
        ...

    def embed(self, text: str) -> Embedding:
        """Return a finite, non-zero 768-dimensional vector."""
        ...
