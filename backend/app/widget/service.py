"""Public widget session services."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.service import (
    create_conversation,
    get_conversation_by_token,
    get_messages,
)

from app.tenancy.service import get_agent_config
from app.tenancy.models import Tenant
from app.conversations.service import get_conversation_by_token, get_messages

async def create_widget_session(
    session: AsyncSession,
    tenant: Tenant,
    *,
    origin_url: str | None = None,
) -> tuple[object, str, str]:
    """Create a visitor conversation and return its public session details."""

    

    conversation, raw_session_token = await create_conversation(
        session,
        origin_url=origin_url,
    )

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
) -> tuple[object, list[object]]:
    """Return a visitor conversation and its messages."""

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