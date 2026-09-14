import pytest
from sqlalchemy import select
from app.common.tenant_context import set_authenticated_identity
from app.conversations.models import ConversationStatus
from app.leads.models import LeadReason
from app.leads.service import create_lead
from app.leads.service import get_lead_by_conversation
from app.leads.service import update_lead_contact

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

@pytest.mark.anyio
async def test_widget_lead_contact_capture(
    db_session,
    existing_tenant,
):
    set_authenticated_identity(
        existing_tenant.owner_user_id,
        existing_tenant.id,
    )

    conversation, session_token, _ = await create_widget_session(
        db_session,
        existing_tenant,
        origin_url="https://example.com",
    )

    lead = await create_lead(
        db_session,
        conversation=conversation,
        reason=LeadReason.EXPLICIT,
        visitor_message="I want to speak with a human.",
    )

    assert conversation.status == ConversationStatus.HANDED_OFF
    assert lead.status.value == "New"

    stored_lead = await get_lead_by_conversation(
        db_session,
        conversation_id=conversation.id,
    )

    assert stored_lead is not None
    assert stored_lead.id == lead.id

    updated_lead = await update_lead_contact(
        db_session,
        lead=stored_lead,
        contact_name="Revanth",
        contact_email="revanth@example.com",
        contact_phone="+919999999999",
        visitor_message="Please contact me about pricing.",
    )

    assert updated_lead.contact_name == "Revanth"
    assert updated_lead.contact_email == "revanth@example.com"
    assert updated_lead.contact_phone == "+919999999999"
    assert updated_lead.visitor_message == "Please contact me about pricing."

    final_lead = await get_lead_by_conversation(
        db_session,
        conversation_id=conversation.id,
    )

    assert final_lead is not None
    assert final_lead.contact_name == "Revanth"
    assert final_lead.contact_email == "revanth@example.com"