import json

import httpx
import pytest

from app.rag.openai_compatible import (
    LLMProviderError,
    OpenAICompatibleClient,
)


class MockStreamResponse:
    """Minimal async streaming response for the client test."""

    status_code = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def aread(self):
        return b""

    async def aiter_lines(self):
        events = [
            {
                "choices": [
                    {
                        "delta": {
                            "content": "Hello"
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {
                            "content": " world"
                        }
                    }
                ]
            },
        ]

        for event in events:
            yield f"data: {json.dumps(event)}"

        yield "data: [DONE]"


class MockAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    def stream(self, method, url, **kwargs):
        assert method == "POST"
        assert url == "https://example.com/chat/completions"

        assert kwargs["json"]["model"] == "test-model"
        assert kwargs["json"]["stream"] is True
        assert kwargs["json"]["max_tokens"] == 400

        messages = kwargs["json"]["messages"]

        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello?"

        return MockStreamResponse()


@pytest.mark.anyio
async def test_openai_compatible_stream(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        MockAsyncClient,
    )

    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="https://example.com",
        model="test-model",
    )

    chunks = []

    async for chunk in client.stream_chat(
        system_prompt="You are helpful.",
        user_message="Hello?",
    ):
        chunks.append(chunk)

    assert chunks == ["Hello", " world"]


def test_client_removes_trailing_slash():
    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="https://example.com/",
        model="test-model",
    )

    assert client.base_url == "https://example.com"


@pytest.mark.anyio
async def test_provider_error(monkeypatch):
    class ErrorResponse(MockStreamResponse):
        status_code = 500

        async def aread(self):
            return b'{"error":"server failure"}'

    class ErrorClient(MockAsyncClient):
        def stream(self, method, url, **kwargs):
            return ErrorResponse()

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        ErrorClient,
    )

    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="https://example.com",
        model="test-model",
    )

    with pytest.raises(LLMProviderError):
        async for _ in client.stream_chat(
            system_prompt="System",
            user_message="Hello",
        ):
            pass