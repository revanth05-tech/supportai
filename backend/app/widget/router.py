"""Public API routes for the support widget."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_db
from app.widget.dependencies import get_widget_tenant
from app.widget.schemas import WidgetSessionCreate, WidgetSessionResponse
from app.widget.service import create_widget_session
from app.tenancy.models import Tenant
from fastapi import Header, HTTPException
from app.widget.service import get_widget_conversation
from app.widget.schemas import WidgetConversationResponse, WidgetMessageResponse


router = APIRouter(prefix="/api/widget", tags=["Widget"])


@router.post("/session", response_model=WidgetSessionResponse)
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

@router.get("/conversation", response_model=WidgetConversationResponse)
async def get_conversation_history(
    session_token: str = Header(..., alias="X-Session-Token"),
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