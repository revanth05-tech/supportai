"""Conversation and message persistence services."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.opaque_tokens import generate_opaque_token, hash_opaque_token
from app.common.tenant_context import get_current_tenant_id
from app.conversations.models import Conversation, Message


async def create_conversation(
    session: AsyncSession,
    *,
    origin_url: str | None = None,
) -> tuple[Conversation, str]:
    """Create a tenant-scoped conversation and return its raw session token."""

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        raise RuntimeError("Tenant context is required.")

    raw_token = generate_opaque_token()
    token_hash = hash_opaque_token(raw_token)

    conversation = Conversation(
        tenant_id=tenant_id,
        session_token=token_hash,
        origin_url=origin_url,
    )

    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)

    return conversation, raw_token


async def get_conversation_by_token(
    session: AsyncSession,
    *,
    token: str,
) -> Conversation | None:
    """Find a conversation using a raw widget session token."""

    token_hash = hash_opaque_token(token)

    statement = select(Conversation).where(
        Conversation.session_token == token_hash
    )

    return await session.scalar(statement)


async def get_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> Conversation | None:
    """Find a conversation by ID within the current tenant."""

    return await session.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id
        )
    )


async def get_messages(
    session: AsyncSession,
    conversation_id: UUID,
) -> list[Message]:
    """Return messages for a conversation in chronological order."""

    result = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )

    return list(result.all())