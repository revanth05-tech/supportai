"""Public API routes for the support widget."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.tenancy.usage import consume_tenant_message
from app.common.dependencies import get_db
from app.conversations.models import ConversationStatus
from app.conversations.service import get_messages
from app.core.rate_limit import widget_rate_limiter
from app.core.sse import encode_sse
from app.leads.models import LeadReason
from app.leads.schemas import LeadContactUpdate, LeadResponse
from app.leads.service import (
    create_lead,
    get_lead_by_conversation,
    notify_lead_owner,
    update_lead_contact,
)
from app.rag.dependencies import get_rag_service
from app.rag.service import RagService
from app.tenancy.models import Tenant
from app.widget.dependencies import (
    get_widget_conversation_for_tenant,
    get_widget_tenant,
)
from app.widget.schemas import (
    WidgetConversationResponse,
    WidgetMessageCreate,
    WidgetMessageResponse,
    WidgetSessionCreate,
    WidgetSessionResponse,
)
from app.widget.service import (
    create_widget_assistant_message,
    create_widget_session,
    create_widget_user_message,
)
router = APIRouter(prefix="/api/widget", tags=["Widget"])


@router.post("/session", response_model=WidgetSessionResponse)
async def create_session(
    payload: WidgetSessionCreate,
    origin: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
):
    tenant = await get_widget_tenant(
        site_key=payload.site_key,
        origin=origin,
        session=session,
    )

    conversation, session_token, welcome_message = await create_widget_session(
        session,
        tenant,
        origin_url=payload.origin_url,
    )
    return WidgetSessionResponse(
        conversation_id=conversation.id,
        session_token=session_token,
        status=conversation.status.value,
        welcome_message=welcome_message,
    )


@router.get("/conversation", response_model=WidgetConversationResponse)
async def get_conversation_history(
    site_key: str,
    session_token: str = Header(..., alias="X-Session-Token"),
    origin: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
):
    tenant, conversation = await get_widget_conversation_for_tenant(
        site_key=site_key,
        session_token=session_token,
        origin=origin,
        session=session,
    )

    messages = await get_messages(
        session,
        conversation.id,
    )

    return WidgetConversationResponse(
        conversation_id=conversation.id,
        status=conversation.status.value,
        messages=[
            WidgetMessageResponse(
                id=message.id,
                role=message.role.value,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.post("/message")
async def send_message(
    payload: WidgetMessageCreate,
    site_key: str,
    request: Request,
    session_token: str = Header(..., alias="X-Session-Token"),
    origin: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
    rag_service: RagService = Depends(get_rag_service),
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{site_key}:{client_ip}"

    if not widget_rate_limiter.allow(rate_limit_key):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": "60"},
        )

    tenant, conversation = await get_widget_conversation_for_tenant(
        site_key=site_key,
        session_token=session_token,
        origin=origin,
        session=session,
    )

    if conversation.status != ConversationStatus.ACTIVE:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=409,
            detail="This conversation has already been handed off.",
    
        )
    quota_available = await consume_tenant_message(
        session,
        tenant_id=tenant.id,
    )

    if not quota_available:
        raise HTTPException(
            status_code=429,
            detail="Daily message limit reached. Please contact the support team.",
            headers={"Retry-After": "3600"},
        )

    messages = await get_messages(
        session,
        conversation.id,
    )

    await create_widget_user_message(
        session,
        conversation=conversation,
        content=payload.message,
    )

    history = [
        {
            "role": message.role.value,
            "content": message.content,
        }
        for message in messages
    ]

    history.append(
        {
            "role": "user",
            "content": payload.message,
        }
    )

    agent_config = tenant.agent_config or {}

    business_name = agent_config.get(
        "business_name",
        tenant.name,
    )
    agent_name = agent_config.get(
        "agent_name",
        "AI Support Agent",
    )
    tone = agent_config.get(
        "tone",
        "professional",
    )
    instructions = agent_config.get(
        "instructions",
        "",
    )

    rag_events = rag_service.stream_response(
        session=session,
        message=payload.message,
        business_name=business_name,
        agent_name=agent_name,
        tone=tone,
        instructions=instructions,
        history=history,
    )

    async def stream_and_persist():
        assistant_content = ""

        async for event, data in rag_events:

            if event == "token":
                token = data.get("content", "")
                assistant_content += token

            elif event == "handoff":
                reason_text = data.get(
                    "reason",
                    "Support handoff required.",
                )

                if reason_text == "Explicit human request":
                    lead_reason = LeadReason.EXPLICIT
                elif reason_text == "quota_overflow":
                    lead_reason = LeadReason.QUOTA_OVERFLOW
                else:
                    lead_reason = LeadReason.NO_GROUNDING

                lead = await create_lead(
                    session,
                    conversation=conversation,
                    reason=lead_reason,
                    stumping_question=payload.message,
                    visitor_message=payload.message,
                )

                await notify_lead_owner(
                    session,
                    lead=lead,
                    business_name=business_name,
                )

                yield encode_sse(
                    {
                        "lead_id": str(lead.id),
                        "reason": reason_text,
                    },
                    event="handoff",
                )

                return

            yield encode_sse(
                data,
                event=event,
            )

        if assistant_content:
            await create_widget_assistant_message(
                session,
                conversation=conversation,
                content=assistant_content,
            )

    return StreamingResponse(
        stream_and_persist(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/contact", response_model=LeadResponse)
async def submit_contact(
    payload: LeadContactUpdate,
    site_key: str,
    session_token: str = Header(..., alias="X-Session-Token"),
    origin: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
):
    _, conversation = await get_widget_conversation_for_tenant(
        site_key=site_key,
        session_token=session_token,
        origin=origin,
        session=session,
    )

    lead = await get_lead_by_conversation(
        session,
        conversation_id=conversation.id,
    )

    if lead is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Lead not found.",
        )

    lead = await update_lead_contact(
        session,
        lead=lead,
        contact_name=payload.contact_name,
        contact_email=str(payload.contact_email),
        contact_phone=payload.contact_phone,
        visitor_message=payload.visitor_message,
    )

    return lead