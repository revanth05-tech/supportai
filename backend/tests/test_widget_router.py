"""Tests for the public widget routes."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException

from app.conversations.models import (
    ConversationStatus,
    Message,
    MessageRole,
)
from app.leads.models import LeadReason
from app.widget.dependencies import get_widget_tenant
from app.widget.router import router, send_message
from app.widget.schemas import WidgetMessageCreate
from app.widget.service import get_widget_conversation


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
        with pytest.raises(ValueError) as exc_info:
            await get_widget_conversation(
                fake_session,
                session_token="invalid-token",
            )

    assert str(exc_info.value) == "Invalid or expired session token."


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


def test_widget_message_route_is_registered():
    routes = [
        (route.path, route.methods)
        for route in router.routes
        if hasattr(route, "path") and hasattr(route, "methods")
    ]

    assert ("/api/widget/message", {"POST"}) in routes


@pytest.mark.anyio
async def test_send_message_rejects_invalid_session():
    fake_session = AsyncMock()

    payload = WidgetMessageCreate(
        message="Hello",
    )

    with patch(
        "app.widget.router.get_widget_conversation",
        new=AsyncMock(
            side_effect=ValueError(
                "Invalid or expired session token."
            )
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await send_message(
                payload=payload,
                session_token="invalid-token",
                session=fake_session,
                rag_service=AsyncMock(),
            )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid or expired session token."


@pytest.mark.anyio
async def test_send_message_streams_rag_response_and_persists_assistant():
    conversation = type(
        "FakeConversation",
        (),
        {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "status": ConversationStatus.ACTIVE,
        },
    )()

    existing_messages = [
        Message(
            id=uuid4(),
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hello",
        ),
    ]

    fake_tenant = type(
        "FakeTenant",
        (),
        {
            "id": conversation.tenant_id,
            "name": "Test Business",
            "agent_config": {
                "business_name": "Test Business",
                "agent_name": "Support Agent",
                "tone": "professional",
                "instructions": "",
            },
        },
    )()

    fake_session = AsyncMock()

    rag_service = AsyncMock()

    async def fake_stream_response(**kwargs):
        yield "token", {"content": "Hello "}
        yield "token", {"content": "there!"}
        yield "done", {}

    rag_service.stream_response = fake_stream_response

    user_message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role=MessageRole.USER,
        content="How can you help?",
    )

    assistant_message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role=MessageRole.ASSISTANT,
        content="Hello there!",
    )

    with patch(
        "app.widget.router.get_widget_conversation",
        new=AsyncMock(
            return_value=(conversation, existing_messages),
        ),
    ), patch(
        "app.widget.router.create_widget_user_message",
        new=AsyncMock(return_value=user_message),
    ) as mock_user_message, patch(
        "app.widget.router.create_widget_assistant_message",
        new=AsyncMock(return_value=assistant_message),
    ) as mock_assistant_message, patch(
        "app.widget.router.select",
    ) as mock_select:

        fake_session.scalar = AsyncMock(
            return_value=fake_tenant,
        )

        result = await send_message(
            payload=WidgetMessageCreate(
                message="How can you help?",
            ),
            session_token="valid-session-token",
            session=fake_session,
            rag_service=rag_service,
        )

        response_body = ""

        async for chunk in result.body_iterator:
            if isinstance(chunk, bytes):
                response_body += chunk.decode()
            else:
                response_body += chunk

    assert "Hello " in response_body
    assert "there!" in response_body
    assert "done" in response_body

    mock_user_message.assert_awaited_once_with(
        fake_session,
        conversation=conversation,
        content="How can you help?",
    )

    mock_assistant_message.assert_awaited_once_with(
        fake_session,
        conversation=conversation,
        content="Hello there!",
    )

    mock_select.assert_called_once()


@pytest.mark.anyio
async def test_send_message_handoff_creates_lead_and_notifies_owner():
    conversation = type(
        "FakeConversation",
        (),
        {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "status": ConversationStatus.ACTIVE,
        },
    )()

    existing_messages = []

    fake_tenant = type(
        "FakeTenant",
        (),
        {
            "id": conversation.tenant_id,
            "name": "Test Business",
            "agent_config": {
                "business_name": "Test Business",
                "agent_name": "Support Agent",
                "tone": "professional",
                "instructions": "",
            },
        },
    )()

    fake_session = AsyncMock()

    rag_service = AsyncMock()

    async def fake_stream_response(**kwargs):
        yield "handoff", {
            "reason": "Explicit human request",
        }

    rag_service.stream_response = fake_stream_response

    user_message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role=MessageRole.USER,
        content="I want to speak to a human.",
    )

    fake_lead = type(
        "FakeLead",
        (),
        {
            "id": uuid4(),
        },
    )()

    with patch(
        "app.widget.router.get_widget_conversation",
        new=AsyncMock(
            return_value=(conversation, existing_messages),
        ),
    ), patch(
        "app.widget.router.create_widget_user_message",
        new=AsyncMock(return_value=user_message),
    ), patch(
        "app.widget.router.create_lead",
        new=AsyncMock(return_value=fake_lead),
    ) as mock_create_lead, patch(
        "app.widget.router.notify_lead_owner",
        new=AsyncMock(return_value=True),
    ) as mock_notify, patch(
        "app.widget.router.select",
    ) as mock_select:

        fake_session.scalar = AsyncMock(
            return_value=fake_tenant,
        )

        result = await send_message(
            payload=WidgetMessageCreate(
                message="I want to speak to a human.",
            ),
            session_token="valid-session-token",
            session=fake_session,
            rag_service=rag_service,
        )

        chunks = []

        async for chunk in result.body_iterator:
            if isinstance(chunk, bytes):
                chunks.append(chunk.decode())
            else:
                chunks.append(chunk)

        body = "".join(chunks)

    mock_create_lead.assert_awaited_once()

    lead_kwargs = mock_create_lead.await_args.kwargs

    assert lead_kwargs["conversation"] == conversation
    assert lead_kwargs["reason"] == LeadReason.EXPLICIT
    assert lead_kwargs["visitor_message"] == (
        "I want to speak to a human."
    )

    mock_notify.assert_awaited_once()

    notify_kwargs = mock_notify.await_args.kwargs

    assert notify_kwargs["lead"] == fake_lead
    assert notify_kwargs["business_name"] == "Test Business"

    assert "handoff" in body
    assert str(fake_lead.id) in body

    mock_select.assert_called_once()