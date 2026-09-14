"""Services for owner dashboard data."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.tenant_context import get_current_tenant_id
from app.conversations.models import Conversation, Message
from app.leads.models import Lead, LeadStatus


async def get_dashboard_summary(
    session: AsyncSession,
) -> dict[str, int]:
    """Return high-level metrics for the current tenant."""

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        raise RuntimeError("Tenant context is required.")

    total_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == tenant_id
        )
    )

    active_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == tenant_id,
            Conversation.status == "Active",
        )
    )

    handed_off_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == tenant_id,
            Conversation.status == "HandedOff",
        )
    )

    total_leads = await session.scalar(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id
        )
    )

    new_leads = await session.scalar(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id,
            Lead.status == LeadStatus.NEW,
        )
    )

    return {
        "total_conversations": total_conversations or 0,
        "active_conversations": active_conversations or 0,
        "handed_off_conversations": handed_off_conversations or 0,
        "total_leads": total_leads or 0,
        "new_leads": new_leads or 0,
    }


async def list_dashboard_conversations(
    session: AsyncSession,
) -> list[Conversation]:
    """Return conversations belonging to the current tenant."""

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        raise RuntimeError("Tenant context is required.")

    result = await session.scalars(
        select(Conversation)
        .where(Conversation.tenant_id == tenant_id)
        .order_by(Conversation.last_message_at.desc())
    )

    return list(result.all())


async def get_dashboard_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> Conversation | None:
    """Return one tenant-scoped conversation."""

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        raise RuntimeError("Tenant context is required.")

    return await session.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )


async def get_dashboard_messages(
    session: AsyncSession,
    conversation_id: UUID,
) -> list[Message]:
    """Return messages for a tenant-scoped dashboard conversation."""

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        raise RuntimeError("Tenant context is required.")

    result = await session.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant_id,
        )
        .order_by(Message.created_at.asc())
    )

    return list(result.all())