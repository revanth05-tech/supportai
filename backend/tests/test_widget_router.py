"""Tests for the public widget routes."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI

from app.conversations.models import Message, MessageRole
from app.widget.router import router
from app.widget.service import get_widget_conversation
from app.widget.dependencies import get_widget_tenant

from fastapi import FastAPI, HTTPException

widget_test_app = FastAPI()
widget_test_app.include_router(router)


def test_widget_session_route_is_registered():
    routes = [
        (route.path, route.methods)
        for route in router.routes
        if hasattr(route, "path") and hasattr(route, "methods")
    ]

    assert ("/api/widget/session", {"POST"}) in routes


def test_widget_conversation_route_is_registered():
    routes = [
        (route.path, route.methods)
        for route in router.routes
        if hasattr(route, "path") and hasattr(route, "methods")
    ]

    assert ("/api/widget/conversation", {"GET"}) in routes


@pytest.mark.anyio
async def test_get_widget_conversation_returns_conversation_and_messages():
    conversation = type(
        "FakeConversation",
        (),
        {
            "id": uuid4(),
        },
    )()

    messages = [
        Message(
            id=uuid4(),
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hello",
        ),
        Message(
            id=uuid4(),
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Hi! How can I help?",
        ),
    ]

    fake_session = AsyncMock()

    with patch(
        "app.widget.service.get_conversation_by_token",
        new=AsyncMock(return_value=conversation),
    ) as mock_lookup, patch(
        "app.widget.service.get_messages",
        new=AsyncMock(return_value=messages),
    ) as mock_messages:

        result_conversation, result_messages = await get_widget_conversation(
            fake_session,
            session_token="test-session-token",
        )

    assert result_conversation is conversation
    assert result_messages == messages

    mock_lookup.assert_awaited_once_with(
        fake_session,
        token="test-session-token",
    )

    mock_messages.assert_awaited_once_with(
        fake_session,
        conversation.id,
    )


@pytest.mark.anyio
async def test_get_widget_conversation_rejects_invalid_token():
    fake_session = AsyncMock()

    with patch(
        "app.widget.service.get_conversation_by_token",
        new=AsyncMock(return_value=None),
    ):
        try:
            await get_widget_conversation(
                fake_session,
                session_token="invalid-token",
            )
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert str(exc) == "Invalid or expired session token."

@pytest.mark.anyio
async def test_get_widget_tenant_rejects_invalid_site_key():
    fake_session = AsyncMock()

    fake_session.scalar = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_widget_tenant(
            site_key="invalid-site-key",
            origin=None,
            session=fake_session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid site key."

@pytest.mark.anyio
async def test_get_widget_tenant_rejects_disallowed_origin():
    fake_tenant = type(
        "FakeTenant",
        (),
        {
            "id": uuid4(),
            "owner_user_id": uuid4(),
            "site_key": "public-site-key",
            "allowed_origins": ["https://example.com"],
        },
    )()

    fake_session = AsyncMock()
    fake_session.scalar = AsyncMock(return_value=fake_tenant)

    with pytest.raises(HTTPException) as exc_info:
        await get_widget_tenant(
            site_key="public-site-key",
            origin="https://evil.example",
            session=fake_session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Origin is not allowed."