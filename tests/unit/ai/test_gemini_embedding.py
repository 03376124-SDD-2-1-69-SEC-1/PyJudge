"""The Gemini adapter validates and normalizes 768-dimensional responses."""

from dataclasses import dataclass
from math import isclose

import pytest

from questly.ai.embeddings import gemini
from questly.ai.embeddings.gemini import (
    GeminiEmbeddingProvider,
    create_gemini_embedding_provider,
    create_gemini_embedding_provider_from_env,
)
from questly.ai.embeddings.ports import EmbeddingError


@dataclass(slots=True)
class FakeEmbedding:
    values: list[float] | None


@dataclass(slots=True)
class FakeResponse:
    embeddings: list[FakeEmbedding] | None


class FakeModels:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def embed_content(
        self, *, model: str, contents: str, config: dict[str, object]
    ) -> FakeResponse:
        self.calls.append((model, contents, config))
        return self.response


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.models = FakeModels(response)


def test_requests_document_embedding_and_normalizes_it() -> None:
    client = FakeClient(FakeResponse([FakeEmbedding([3.0, 4.0] + [0.0] * 766)]))
    provider = GeminiEmbeddingProvider(client)

    vector = provider.embed("โจทย์")

    assert provider.model == "gemini-embedding-001"
    assert client.models.calls == [
        (
            "gemini-embedding-001",
            "โจทย์",
            {"output_dimensionality": 768, "task_type": "RETRIEVAL_DOCUMENT"},
        )
    ]
    assert len(vector) == 768
    assert isclose(vector[0], 0.6)
    assert isclose(vector[1], 0.8)


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(None),
        FakeResponse([]),
        FakeResponse([FakeEmbedding(None)]),
        FakeResponse([FakeEmbedding([1.0])]),
        FakeResponse([FakeEmbedding([0.0] * 768)]),
        FakeResponse([FakeEmbedding([float("nan")] + [0.0] * 767)]),
    ],
)
def test_refuses_unusable_provider_responses(response: FakeResponse) -> None:
    with pytest.raises(EmbeddingError):
        GeminiEmbeddingProvider(FakeClient(response)).embed("text")


def test_refuses_empty_text_without_provider_call() -> None:
    client = FakeClient(FakeResponse([FakeEmbedding([1.0] * 768)]))

    with pytest.raises(EmbeddingError, match="empty text"):
        GeminiEmbeddingProvider(client).embed(" \n ")

    assert client.models.calls == []


def test_factory_requires_explicit_key_before_importing_sdk() -> None:
    with pytest.raises(ValueError, match="API key"):
        create_gemini_embedding_provider(" ")


def test_env_factory_requires_key_without_importing_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini, "load_dotenv", lambda **_kwargs: None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="API key"):
        create_gemini_embedding_provider_from_env()


def test_env_factory_passes_key_without_exposing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    sentinel = GeminiEmbeddingProvider(FakeClient(FakeResponse(None)))

    def create(api_key: str) -> GeminiEmbeddingProvider:
        observed.append(api_key)
        return sentinel

    monkeypatch.setattr(gemini, "load_dotenv", lambda **_kwargs: None)
    monkeypatch.setattr(gemini, "create_gemini_embedding_provider", create)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-value")

    assert create_gemini_embedding_provider_from_env() is sentinel
    assert observed == ["test-only-value"]
