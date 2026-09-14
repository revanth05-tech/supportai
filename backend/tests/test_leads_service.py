"""Tests for lead services."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.common.tenant_context import set_authenticated_identity
from app.conversations.models import Conversation, ConversationStatus
from app.identity.models import User
from app.leads.models import Lead, LeadReason, LeadStatus
from app.leads.service import (
    create_lead,
    notify_lead_owner,
    update_lead_status,
)


@pytest.mark.anyio
async def test_create_lead_marks_conversation_as_handed_off(
    db_session,
    existing_tenant,
):
    set_authenticated_identity(
        existing_tenant.owner_user_id,
        existing_tenant.id,
    )

    conversation = Conversation(
        tenant_id=existing_tenant.id,
        session_token="test-session-hash",
        origin_url="https://example.com",
    )

    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    lead = await create_lead(
        db_session,
        conversation=conversation,
        reason=LeadReason.EXPLICIT,
        visitor_message="I want to speak to a human.",
    )

    assert lead.id is not None
    assert lead.tenant_id == existing_tenant.id
    assert lead.conversation_id == conversation.id
    assert lead.reason == LeadReason.EXPLICIT
    assert lead.status == LeadStatus.NEW
    assert lead.visitor_message == "I want to speak to a human."
    assert conversation.status == ConversationStatus.HANDED_OFF

    stored_lead = await db_session.scalar(
        select(Lead).where(Lead.id == lead.id)
    )

    assert stored_lead is not None
    assert stored_lead.conversation_id == conversation.id


@pytest.mark.anyio
async def test_update_lead_status(
    db_session,
    existing_tenant,
):
    set_authenticated_identity(
        existing_tenant.owner_user_id,
        existing_tenant.id,
    )

    conversation = Conversation(
        tenant_id=existing_tenant.id,
        session_token="status-test-session",
    )

    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    lead = await create_lead(
        db_session,
        conversation=conversation,
        reason=LeadReason.EXPLICIT,
        visitor_message="I need help from your team.",
    )

    assert lead.status == LeadStatus.NEW

    updated_lead = await update_lead_status(
        db_session,
        lead=lead,
        status=LeadStatus.CONTACTED,
    )

    assert updated_lead.status == LeadStatus.CONTACTED

    updated_lead = await update_lead_status(
        db_session,
        lead=updated_lead,
        status=LeadStatus.CLOSED,
    )

    assert updated_lead.status == LeadStatus.CLOSED


@pytest.mark.anyio
async def test_notify_lead_owner(
    db_session,
    existing_tenant,
):
    set_authenticated_identity(
        existing_tenant.owner_user_id,
        existing_tenant.id,
    )

    conversation = Conversation(
        tenant_id=existing_tenant.id,
        session_token="email-notification-session",
    )

    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    lead = await create_lead(
        db_session,
        conversation=conversation,
        reason=LeadReason.EXPLICIT,
        visitor_message="I want to speak with someone.",
    )

    with patch(
        "app.leads.service.send_lead_notification",
        new=AsyncMock(return_value=True),
    ) as mock_notify:
        result = await notify_lead_owner(
            db_session,
            lead=lead,
            business_name="Test Business",
        )

    assert result is True

    mock_notify.assert_awaited_once()

    call_kwargs = mock_notify.await_args.kwargs

    owner = await db_session.scalar(
        select(User).where(
            User.id == existing_tenant.owner_user_id
        )
    )

    assert owner is not None
    assert call_kwargs["owner_email"] == owner.email
    assert call_kwargs["business_name"] == "Test Business"
    assert call_kwargs["lead"] == lead