"""OpenAI-compatible streaming chat client."""

import json
from collections.abc import AsyncIterator

import httpx

from app.rag.llm import LLMClient


class LLMProviderError(RuntimeError):
    """Raised when the LLM provider cannot complete a request."""


class OpenAICompatibleClient(LLMClient):
    """Client for providers exposing the OpenAI chat-completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def stream_chat(
        self,
        *,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        if history:
            messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": 400,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise LLMProviderError(
                            f"LLM provider returned HTTP "
                            f"{response.status_code}: "
                            f"{body.decode(errors='replace')[:500]}"
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue

                        data = line[5:].strip()

                        if data == "[DONE]":
                            break

                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        choices = event.get("choices", [])
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})
                        content = delta.get("content")

                        if content:
                            yield content

        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Unable to reach LLM provider: {exc}"
            ) from exc