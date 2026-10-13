"""The OpenRouter adapter validates and normalizes 768-dimensional responses."""

import json
from dataclasses import dataclass
from math import isclose

import httpx
import pytest
from openrouter.errors import NoResponseError, OpenRouterError

from questly.ai.embeddings import openrouter
from questly.ai.embeddings.openrouter import (
    OpenRouterEmbeddingProvider,
    create_openrouter_embedding_provider,
)
from questly.ai.embeddings.ports import EmbeddingError

MODEL = "google/gemini-embedding-001"


@dataclass(slots=True)
class FakeEmbedding:
    embedding: list[float] | None


@dataclass(slots=True)
class FakeResponse:
    data: list[FakeEmbedding] | None


class FakeEmbeddings:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def generate(self, **kwargs: object) -> FakeResponse:
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeClient:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.embeddings = FakeEmbeddings(response)


def test_requests_document_embedding_and_normalizes_it() -> None:
    client = FakeClient(FakeResponse([FakeEmbedding([3.0, 4.0] + [0.0] * 766)]))
    provider = OpenRouterEmbeddingProvider(client, MODEL)

    vector = provider.embed("โจทย์")

    assert provider.model == MODEL
    assert client.embeddings.calls == [
        {
            "model": MODEL,
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
        OpenRouterEmbeddingProvider(FakeClient(response), MODEL).embed("text")


@pytest.mark.parametrize(
    "error",
    [
        OpenRouterError(
            "rate limited",
            httpx.Response(429, request=httpx.Request("POST", "https://x")),
        ),
        NoResponseError(),
        httpx.ReadTimeout("timed out"),
    ],
    ids=["openrouter-error", "no-response", "timeout"],
)
def test_sdk_failures_become_embedding_errors(error: Exception) -> None:
    provider = OpenRouterEmbeddingProvider(FakeClient(error), MODEL)

    with pytest.raises(EmbeddingError) as raised:
        provider.embed("text")

    assert raised.value.__cause__ is error


def test_refuses_empty_text_without_provider_call() -> None:
    client = FakeClient(FakeResponse([FakeEmbedding([1.0] * 768)]))

    with pytest.raises(EmbeddingError, match="empty text"):
        OpenRouterEmbeddingProvider(client, MODEL).embed(" \n ")

    assert client.embeddings.calls == []


def test_factory_requires_explicit_key_before_creating_client() -> None:
    with pytest.raises(ValueError, match="API key"):
        create_openrouter_embedding_provider(" ", MODEL)


def test_factory_builds_the_sdk_client_and_requests_the_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def reply(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "other/embedder",
                "data": [
                    {
                        "object": "embedding",
                        "index": 0,
                        "embedding": [3.0, 4.0] + [0.0] * 766,
                    }
                ],
            },
        )

    provider = create_openrouter_embedding_provider("test-only-value", "other/embedder")
    sdk = provider._client
    assert isinstance(sdk, openrouter.OpenRouter)
    sdk.sdk_configuration.client = httpx.Client(transport=httpx.MockTransport(reply))

    vector = provider.embed("โจทย์")

    assert isclose(vector[0], 0.6)
    assert requests[0].url == "https://openrouter.ai/api/v1/embeddings"
    assert requests[0].headers["authorization"] == "Bearer test-only-value"
    assert json.loads(requests[0].content) == {
        "input": "โจทย์",
        "model": "other/embedder",
        "dimensions": 768,
        "encoding_format": "float",
    }
