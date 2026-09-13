from collections.abc import AsyncIterator

import pytest

from app.core.sse import encode_sse, stream_sse_events


def test_encode_sse_event():
    result = encode_sse(
        {"content": "Hello"},
        event="token",
    )

    assert result == (
        'event: token\n'
        'data: {"content":"Hello"}\n\n'
    )


@pytest.mark.anyio
async def test_stream_sse_events():
    async def events() -> AsyncIterator[tuple[str, dict]]:
        yield "token", {"content": "Hello"}
        yield "token", {"content": " world"}
        yield "done", {}

    output = []

    async for event in stream_sse_events(events()):
        output.append(event)

    assert output == [
        'event: token\ndata: {"content":"Hello"}\n\n',
        'event: token\ndata: {"content":" world"}\n\n',
        'event: done\ndata: {}\n\n',
    ]