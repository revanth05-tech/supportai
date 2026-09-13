"""SSE formatting primitive for the future RAG streaming service."""

import json
from collections.abc import AsyncIterator
from typing import Any


def encode_sse(data: Any, *, event: str | None = None) -> str:
    """Format one JSON SSE message without coupling it to a specific endpoint."""
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(data, separators=(',', ':'))}\n\n"


async def single_sse_event(data: Any, *, event: str | None = None) -> AsyncIterator[str]:
    """Minimal async generator compatible with StreamingResponse."""
    yield encode_sse(data, event=event)

async def stream_sse_events(
    events: AsyncIterator[tuple[str, Any]],
) -> AsyncIterator[str]:
    """Convert an async event stream into SSE messages."""

    async for event, data in events:
        yield encode_sse(data, event=event)