import pytest
from sqlalchemy import select

from app.conversations.models import Conversation, Message, MessageRole
from app.widget.dependencies import get_widget_tenant
from app.widget.service import (
    create_widget_session,
    create_widget_user_message,
)


@pytest.mark.anyio
async def test_widget_session_is_created_in_database(
    db_session,
    existing_tenant,
):
    tenant = await get_widget_tenant(
        site_key=existing_tenant.site_key,
        origin=None,
        session=db_session,
    )

    conversation, session_token, welcome_message = await create_widget_session(
        db_session,
        tenant,
        origin_url="http://localhost:3000",
    )

    assert conversation.tenant_id == tenant.id
    assert conversation.session_token != session_token
    assert len(session_token) > 20
    assert welcome_message == "Hi! How can I help you today?"

    stored = await db_session.scalar(
        select(Conversation).where(
            Conversation.id == conversation.id
        )
    )

    assert stored is not None
    assert stored.tenant_id == tenant.id
    assert stored.session_token != session_token


@pytest.mark.anyio
async def test_widget_user_message_is_persisted(
    db_session,
    existing_tenant,
):
    tenant = await get_widget_tenant(
        site_key=existing_tenant.site_key,
        origin=None,
        session=db_session,
    )

    conversation, _, _ = await create_widget_session(
        db_session,
        tenant,
        origin_url="http://localhost:3000",
    )

    message = await create_widget_user_message(
        db_session,
        conversation=conversation,
        content="What are your business hours?",
    )

    assert message.id is not None
    assert message.conversation_id == conversation.id
    assert message.tenant_id == tenant.id
    assert message.role == MessageRole.USER
    assert message.content == "What are your business hours?"

    stored = await db_session.scalar(
        select(Message).where(
            Message.id == message.id
        )
    )

    assert stored is not None
    assert stored.role == MessageRole.USER
    assert stored.content == "What are your business hours?"