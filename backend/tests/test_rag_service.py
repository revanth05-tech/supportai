from collections.abc import AsyncIterator

import pytest

from app.knowledge.embedder import Embedder
from app.rag.llm import LLMClient
from app.rag.service import RagService


class FakeEmbedder(Embedder):
    """Deterministic embedder for service tests."""

    async def embed(self, text: str) -> list[float]:
        return [0.1] * self.dimension


class FakeLLMClient(LLMClient):
    """Fake streaming LLM client."""

    def __init__(self) -> None:
        self.system_prompt = None
        self.user_message = None

    async def stream_chat(
        self,
        *,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        self.system_prompt = system_prompt
        self.user_message = user_message

        yield "Hello"
        yield " there"


@pytest.mark.anyio
async def test_rag_service_hands_off_when_nothing_is_retrieved(
    monkeypatch,
):
    async def fake_retrieve_chunks(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "app.rag.service.retrieve_chunks",
        fake_retrieve_chunks,
    )

    llm = FakeLLMClient()

    service = RagService(
        embedder=FakeEmbedder(),
        llm_client=llm,
    )

    events = []

    async for event in service.stream_response(
        session=None,
        message="What is your refund policy?",
        business_name="Acme",
        agent_name="Ava",
        tone="friendly",
        instructions="",
    ):
        events.append(event)

    assert events == [
        (
            "handoff",
            {
                "reason": "Insufficient knowledge grounding",
            },
        )
    ]

    assert llm.system_prompt is None


@pytest.mark.anyio
async def test_rag_service_streams_grounded_response(
    monkeypatch,
):
    class FakeChunk:
        content = "Our refund policy allows refunds within 30 days."
        similarity = 0.91

    async def fake_retrieve_chunks(*args, **kwargs):
        return [FakeChunk()]

    monkeypatch.setattr(
        "app.rag.service.retrieve_chunks",
        fake_retrieve_chunks,
    )

    llm = FakeLLMClient()

    service = RagService(
        embedder=FakeEmbedder(),
        llm_client=llm,
    )

    events = []

    async for event in service.stream_response(
        session=None,
        message="What is your refund policy?",
        business_name="Acme",
        agent_name="Ava",
        tone="friendly",
        instructions="Keep answers short.",
    ):
        events.append(event)

    assert events == [
        ("token", {"content": "Hello"}),
        ("token", {"content": " there"}),
        ("done", {}),
    ]

    assert llm.user_message == "What is your refund policy?"
    assert "Our refund policy allows refunds within 30 days." in (
        llm.system_prompt
    )
    assert "Keep answers short." in llm.system_prompt


@pytest.mark.anyio
async def test_rag_service_detects_explicit_human_request(
    monkeypatch,
):
    class FakeChunk:
        content = "Our support team is available."
        similarity = 0.95

    async def fake_retrieve_chunks(*args, **kwargs):
        return [FakeChunk()]

    monkeypatch.setattr(
        "app.rag.service.retrieve_chunks",
        fake_retrieve_chunks,
    )

    llm = FakeLLMClient()

    service = RagService(
        embedder=FakeEmbedder(),
        llm_client=llm,
    )

    events = []

    async for event in service.stream_response(
        session=None,
        message="I want to talk to a human",
        business_name="Acme",
        agent_name="Ava",
        tone="friendly",
        instructions="",
    ):
        events.append(event)

    assert events == [
        (
            "handoff",
            {
                "reason": "Explicit human request",
            },
        )
    ]

    assert llm.system_prompt is None