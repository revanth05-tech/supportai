"""Tests for owner dashboard APIs."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.common.tenant_context import (
    reset_current_tenant_id,
    set_authenticated_identity,
    system_access,
)
from app.conversations.models import (
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
)
from app.identity.jwt_service import create_access_token
from app.identity.models import User
from app.leads.models import Lead, LeadReason, LeadStatus
from app.main import app
from app.tenancy.models import Tenant


def _auth_headers(existing_tenant: Tenant) -> dict[str, str]:
    """Create a valid dashboard Bearer token for the tenant owner."""

    token = create_access_token(
        user_id=existing_tenant.owner_user_id,
        email=f"widget-test-{existing_tenant.owner_user_id}@example.com",
        tenant_id=str(existing_tenant.id),
    )

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.mark.anyio
async def test_dashboard_summary(
    db_session,
    existing_tenant,
):
    """Dashboard summary returns metrics for the current tenant."""

    token = set_authenticated_identity(
        existing_tenant.owner_user_id,
        existing_tenant.id,
    )

    try:
        conversation = Conversation(
            tenant_id=existing_tenant.id,
            session_token=f"summary-session-{uuid4()}",
            status=ConversationStatus.ACTIVE,
        )

        handed_off = Conversation(
            tenant_id=existing_tenant.id,
            session_token=f"handoff-session-{uuid4()}",
            status=ConversationStatus.HANDED_OFF,
        )

        db_session.add_all([conversation, handed_off])
        await db_session.flush()

        lead = Lead(
            tenant_id=existing_tenant.id,
            conversation_id=handed_off.id,
            reason=LeadReason.EXPLICIT,
            status=LeadStatus.NEW,
        )

        db_session.add(lead)
        await db_session.commit()

        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/dashboard/summary",
                headers=_auth_headers(existing_tenant),
            )
    finally:
        reset_current_tenant_id(token)

    assert response.status_code == 200

    data = response.json()

    assert data["total_conversations"] == 2
    assert data["active_conversations"] == 1
    assert data["handed_off_conversations"] == 1
    assert data["total_leads"] == 1
    assert data["new_leads"] == 1


@pytest.mark.anyio
async def test_dashboard_conversations(
    db_session,
    existing_tenant,
):
    """Dashboard conversation list returns tenant conversations."""

    token = set_authenticated_identity(
        existing_tenant.owner_user_id,
        existing_tenant.id,
    )

    try:
        conversation = Conversation(
            tenant_id=existing_tenant.id,
            session_token=f"conversation-session-{uuid4()}",
            status=ConversationStatus.ACTIVE,
            origin_url="https://example.com",
        )

        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/dashboard/conversations",
                headers=_auth_headers(existing_tenant),
            )
    finally:
        reset_current_tenant_id(token)

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(conversation.id)
    assert data[0]["status"] == "Active"
    assert data[0]["origin_url"] == "https://example.com"


@pytest.mark.anyio
async def test_dashboard_conversation_detail(
    db_session,
    existing_tenant,
):
    """Dashboard conversation detail returns messages chronologically."""

    token = set_authenticated_identity(
        existing_tenant.owner_user_id,
        existing_tenant.id,
    )

    try:
        conversation = Conversation(
            tenant_id=existing_tenant.id,
            session_token=f"detail-session-{uuid4()}",
            status=ConversationStatus.ACTIVE,
        )

        db_session.add(conversation)
        await db_session.flush()

        first_message = Message(
            conversation_id=conversation.id,
            tenant_id=existing_tenant.id,
            role=MessageRole.USER,
            content="What are your business hours?",
        )

        second_message = Message(
            conversation_id=conversation.id,
            tenant_id=existing_tenant.id,
            role=MessageRole.ASSISTANT,
            content="We are open from 9 AM to 6 PM.",
            was_grounded=True,
            top_similarity=0.82,
            model_used="test-model",
            latency_ms=120,
        )

        db_session.add_all([first_message, second_message])
        await db_session.commit()

        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/dashboard/conversations/{conversation.id}",
                headers=_auth_headers(existing_tenant),
            )
    finally:
        reset_current_tenant_id(token)

    assert response.status_code == 200

    data = response.json()

    assert data["conversation"]["id"] == str(conversation.id)
    assert len(data["messages"]) == 2

    assert data["messages"][0]["role"] == "User"
    assert data["messages"][0]["content"] == "What are your business hours?"

    assert data["messages"][1]["role"] == "Assistant"
    assert data["messages"][1]["was_grounded"] is True
    assert data["messages"][1]["top_similarity"] == 0.82


@pytest.mark.anyio
async def test_dashboard_cannot_access_another_tenant_conversation(
    db_session,
    existing_tenant,
):
    """A tenant cannot access another tenant's conversation."""

    other_user_id = str(uuid4())

    other_user = User(
        id=other_user_id,
        email=f"other-test-{other_user_id}@example.com",
        display_name="Other Test User",
        password_hash="test-password-hash",
    )

    other_tenant = Tenant(
        owner_user_id=other_user_id,
        name="Other Test Tenant",
        site_key=f"other-test-{uuid4()}",
        allowed_origins=[],
        agent_config={},
    )

    with system_access():
        db_session.add(other_user)
        db_session.add(other_tenant)
        await db_session.flush()

        foreign_conversation = Conversation(
            tenant_id=other_tenant.id,
            session_token=f"foreign-session-{uuid4()}",
            status=ConversationStatus.ACTIVE,
        )

        db_session.add(foreign_conversation)
        await db_session.commit()
        await db_session.refresh(foreign_conversation)

    token = set_authenticated_identity(
        existing_tenant.owner_user_id,
        existing_tenant.id,
    )

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/dashboard/conversations/{foreign_conversation.id}",
                headers=_auth_headers(existing_tenant),
            )
    finally:
        reset_current_tenant_id(token)

    assert response.status_code == 404

    with system_access():
        await db_session.delete(other_tenant)
        await db_session.delete(other_user)
        await db_session.commit()