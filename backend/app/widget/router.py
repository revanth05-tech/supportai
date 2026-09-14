"""Public API routes for the support widget."""

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_db
from app.core.sse import stream_sse_events
from app.rag.dependencies import get_rag_service
from app.rag.service import RagService
from app.tenancy.models import Tenant
from app.widget.dependencies import get_widget_tenant
from app.widget.schemas import (
    WidgetConversationResponse,
    WidgetMessageCreate,
    WidgetMessageResponse,
    WidgetSessionCreate,
    WidgetSessionResponse,
)
from app.widget.service import (
    create_widget_session,
    create_widget_user_message,
    get_widget_conversation,
)


router = APIRouter(
    prefix="/api/widget",
    tags=["Widget"],
)


@router.post(
    "/session",
    response_model=WidgetSessionResponse,
)
async def create_session(
    payload: WidgetSessionCreate,
    tenant: Tenant = Depends(get_widget_tenant),
    session: AsyncSession = Depends(get_db),
) -> WidgetSessionResponse:
    """Create a public visitor conversation session."""

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


@router.get(
    "/conversation",
    response_model=WidgetConversationResponse,
)
async def get_conversation_history(
    session_token: str = Header(
        ...,
        alias="X-Session-Token",
    ),
    session: AsyncSession = Depends(get_db),
) -> WidgetConversationResponse:
    """Return conversation history for a public widget session."""

    try:
        conversation, messages = await get_widget_conversation(
            session,
            session_token=session_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc

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
    session_token: str = Header(
        ...,
        alias="X-Session-Token",
    ),
    session: AsyncSession = Depends(get_db),
    rag_service: RagService = Depends(get_rag_service),
):
    """Receive a visitor message and stream the AI response."""

    # 1. Validate the widget session token.
    try:
        conversation, messages = await get_widget_conversation(
            session,
            session_token=session_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc

    # 2. Load the tenant explicitly.
    tenant = await session.scalar(
        select(Tenant).where(Tenant.id == conversation.tenant_id)
    )

    if tenant is None:
        raise HTTPException(
            status_code=401,
            detail="Conversation tenant not found.",
        )

    # 3. Persist the visitor message.
    await create_widget_user_message(
        session,
        conversation=conversation,
        content=payload.message,
    )

    # 4. Build history from persisted messages.
    history = [
        {
            "role": message.role.value,
            "content": message.content,
        }
        for message in messages
    ]

    # Include the current visitor message.
    history.append(
        {
            "role": "user",
            "content": payload.message,
        }
    )

    # 5. Resolve the tenant's agent configuration.
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

    # 6. Run the existing RAG pipeline.
    events = rag_service.stream_response(
        session=session,
        message=payload.message,
        business_name=business_name,
        agent_name=agent_name,
        tone=tone,
        instructions=instructions,
        history=history,
    )

    # 7. Stream the RAG events to the widget.
    return StreamingResponse(
        stream_sse_events(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )