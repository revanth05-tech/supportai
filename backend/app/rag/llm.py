"""LLM provider abstraction."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMClient(ABC):
    """Provider-independent interface for chat completion."""

    @abstractmethod
    async def stream_chat(
        self,
        *,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream generated text tokens."""
        yield ""