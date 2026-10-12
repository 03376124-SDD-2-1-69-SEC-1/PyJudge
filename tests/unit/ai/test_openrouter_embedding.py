"""The OpenRouter adapter validates and normalizes 768-dimensional responses."""

import sys
from dataclasses import dataclass
from math import isclose
from types import SimpleNamespace

import pytest

from questly.ai.embeddings import openrouter
from questly.ai.embeddings.openrouter import (
    OpenRouterEmbeddingProvider,
    create_openrouter_embedding_provider,
    create_openrouter_embedding_provider_from_env,
)
from questly.ai.embeddings.ports import EmbeddingError


@dataclass(slots=True)
class FakeEmbedding:
    embedding: list[float] | None


@dataclass(slots=True)
class FakeResponse:
    data: list[FakeEmbedding] | None


class FakeEmbeddings:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> FakeResponse:
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.embeddings = FakeEmbeddings(response)


def test_requests_document_embedding_and_normalizes_it() -> None:
    client = FakeClient(FakeResponse([FakeEmbedding([3.0, 4.0] + [0.0] * 766)]))
    provider = OpenRouterEmbeddingProvider(client)

    vector = provider.embed("โจทย์")

    assert provider.model == "google/gemini-embedding-001"
    assert client.embeddings.calls == [
        {
            "model": "google/gemini-embedding-001",
            "input": "โจทย์",
            "dimensions": 768,
            "encoding_format": "float",
        }
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
        OpenRouterEmbeddingProvider(FakeClient(response)).embed("text")


def test_refuses_empty_text_without_provider_call() -> None:
    client = FakeClient(FakeResponse([FakeEmbedding([1.0] * 768)]))

    with pytest.raises(EmbeddingError, match="empty text"):
        OpenRouterEmbeddingProvider(client).embed(" \n ")

    assert client.embeddings.calls == []


def test_factory_requires_explicit_key_before_creating_client() -> None:
    with pytest.raises(ValueError, match="API key"):
        create_openrouter_embedding_provider(" ")


def test_factory_uses_existing_sdk_with_openrouter_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[dict[str, object]] = []
    fake = FakeClient(FakeResponse(None))

    def make_client(api_key: str) -> FakeClient:
        observed.append({"api_key": api_key})
        return fake

    monkeypatch.setattr(openrouter, "_new_client", make_client)

    provider = create_openrouter_embedding_provider("test-only-value")

    assert isinstance(provider, OpenRouterEmbeddingProvider)
    assert observed == [{"api_key": "test-only-value"}]


def test_client_uses_openrouter_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[dict[str, object]] = []
    fake = FakeClient(FakeResponse(None))

    def make_client(**kwargs: object) -> FakeClient:
        observed.append(kwargs)
        return fake

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=make_client))

    assert openrouter._new_client("test-only-value") is fake
    assert observed == [
        {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "test-only-value",
            "timeout": 60.0,
        }
    ]


def test_env_factory_requires_key_without_creating_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(openrouter, "load_dotenv", lambda **_kwargs: None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="API key"):
        create_openrouter_embedding_provider_from_env()


def test_env_factory_passes_key_without_exposing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    sentinel = OpenRouterEmbeddingProvider(FakeClient(FakeResponse(None)))

    def create(api_key: str) -> OpenRouterEmbeddingProvider:
        observed.append(api_key)
        return sentinel

    monkeypatch.setattr(openrouter, "load_dotenv", lambda **_kwargs: None)
    monkeypatch.setattr(openrouter, "create_openrouter_embedding_provider", create)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-value")

    assert create_openrouter_embedding_provider_from_env() is sentinel
    assert observed == ["test-only-value"]
