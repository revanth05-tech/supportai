"""Services for creating and updating support leads."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.common.tenant_context import get_current_tenant_id
from app.conversations.models import Conversation, ConversationStatus
from app.leads.models import Lead, LeadReason, LeadStatus
from app.common.email import email_service

from app.identity.models import User

async def create_lead(
    session: AsyncSession,
    *,
    conversation: Conversation,
    reason: LeadReason,
    stumping_question: str | None = None,
    visitor_message: str | None = None,
) -> Lead:
    """Create a lead and mark its conversation as handed off."""

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        raise RuntimeError("Tenant context is required.")

    if conversation.tenant_id != tenant_id:
        raise ValueError("Conversation does not belong to the current tenant.")

    lead = Lead(
        tenant_id=tenant_id,
        conversation_id=conversation.id,
        reason=reason,
        stumping_question=stumping_question,
        visitor_message=visitor_message,
        status=LeadStatus.NEW,
    )

    conversation.status = ConversationStatus.HANDED_OFF

    session.add(lead)

    await session.commit()
    await session.refresh(lead)

    return lead


async def get_lead(
    session: AsyncSession,
    *,
    lead_id,
) -> Lead | None:
    """Retrieve a tenant-scoped lead by ID."""

    from sqlalchemy import select

    result = await session.scalar(
        select(Lead).where(Lead.id == lead_id)
    )

    return result


async def update_lead_contact(
    session: AsyncSession,
    *,
    lead: Lead,
    contact_name: str,
    contact_email: str,
    contact_phone: str | None = None,
    visitor_message: str | None = None,
) -> Lead:
    """Attach visitor contact information to a lead."""

    lead.contact_name = contact_name
    lead.contact_email = contact_email
    lead.contact_phone = contact_phone

    if visitor_message is not None:
        lead.visitor_message = visitor_message

    await session.commit()
    await session.refresh(lead)

    return lead


async def update_lead_status(
    session: AsyncSession,
    *,
    lead: Lead,
    status: LeadStatus,
) -> Lead:
    """Update the lifecycle status of a lead."""

    lead.status = status

    await session.commit()
    await session.refresh(lead)

    return lead

async def get_lead_by_conversation(
    session: AsyncSession,
    *,
    conversation_id,
):
    result = await session.scalar(
        select(Lead).where(
            Lead.conversation_id == conversation_id
        )
    )
    return result

async def send_lead_notification(
    *,
    lead: Lead,
    owner_email: str,
    business_name: str,
) -> bool:
    """Notify the tenant owner about a new support lead."""

    visitor_name = lead.contact_name or "Unknown"
    visitor_email = lead.contact_email or "Not provided"
    visitor_phone = lead.contact_phone or "Not provided"
    visitor_message = lead.visitor_message or "Not provided"

    html = f"""
    <h2>New Support Lead</h2>

    <p>
        A visitor has requested help from your support team.
    </p>

    <h3>Business</h3>
    <p>{business_name}</p>

    <h3>Visitor</h3>
    <p><strong>Name:</strong> {visitor_name}</p>
    <p><strong>Email:</strong> {visitor_email}</p>
    <p><strong>Phone:</strong> {visitor_phone}</p>

    <h3>Message</h3>
    <p>{visitor_message}</p>

    <h3>Reason</h3>
    <p>{lead.reason.value}</p>
    """

    return await email_service.send_email(
        to=owner_email,
        subject=f"New support lead — {business_name}",
        html=html,
    )

async def notify_lead_owner(
    session: AsyncSession,
    *,
    lead: Lead,
    business_name: str,
) -> bool:
    """Notify the tenant owner about a newly created lead."""

    from app.tenancy.models import Tenant

    tenant = await session.scalar(
        select(Tenant).where(
            Tenant.id == lead.tenant_id
        )
    )

    if tenant is None:
        return False

    owner = await session.scalar(
        select(User).where(
            User.id == tenant.owner_user_id
        )
    )

    if owner is None or not owner.email:
        return False

    return await send_lead_notification(
        lead=lead,
        owner_email=owner.email,
        business_name=business_name,
    )