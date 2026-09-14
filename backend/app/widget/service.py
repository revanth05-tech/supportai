"""Public widget session and conversation services."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.opaque_tokens import (
    generate_opaque_token,
    hash_opaque_token,
)
from app.common.tenant_context import get_current_tenant_id
from app.conversations.models import Conversation, Message, MessageRole
from app.conversations.service import (
    get_conversation_by_token,
    get_messages,
)
from app.tenancy.models import Tenant
from app.tenancy.service import get_agent_config


async def create_widget_session(
    session: AsyncSession,
    tenant: Tenant,
    *,
    origin_url: str | None = None,
) -> tuple[Conversation, str, str]:
    """Create a public widget conversation and return its raw session token."""

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        raise ValueError("Tenant context is not available.")

    raw_session_token = generate_opaque_token()
    token_hash = hash_opaque_token(raw_session_token)

    conversation = Conversation(
        tenant_id=tenant.id,
        session_token=token_hash,
        origin_url=origin_url,
    )

    session.add(conversation)

    await session.commit()
    await session.refresh(conversation)

    agent_config = get_agent_config(tenant)

    welcome_message = agent_config.get(
        "welcome_message",
        "Hi! How can I help you today?",
    )

    return conversation, raw_session_token, welcome_message


async def get_widget_conversation(
    session: AsyncSession,
    *,
    session_token: str,
) -> tuple[Conversation, list[Message]]:
    """Get a widget conversation and its persisted messages."""

    conversation = await get_conversation_by_token(
        session,
        token=session_token,
    )

    if conversation is None:
        raise ValueError("Invalid or expired session token.")

    messages = await get_messages(
        session,
        conversation.id,
    )

    return conversation, messages


async def create_widget_user_message(
    session: AsyncSession,
    *,
    conversation: Conversation,
    content: str,
) -> Message:
    """Persist a visitor message for a widget conversation."""

    message = Message(
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role=MessageRole.USER,
        content=content,
    )

    session.add(message)

    conversation.last_message_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(message)

    return message
async def create_widget_assistant_message(
    session: AsyncSession,
    *,
    conversation: Conversation,
    content: str,
) -> Message:
    """Persist the completed assistant response for a widget conversation."""

    message = Message(
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role=MessageRole.ASSISTANT,
        content=content,
    )

    session.add(message)

    conversation.last_message_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(message)

    return message
async def create_widget_assistant_message(
    session: AsyncSession,
    *,
    conversation: Conversation,
    content: str,
) -> Message:
    """Persist the completed assistant response for a widget conversation."""

    message = Message(
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role=MessageRole.ASSISTANT,
        content=content,
    )

    session.add(message)

    conversation.last_message_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(message)

    return message