"""API routes for the owner dashboard."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_tenant, get_db
from app.dashboard.schemas import (
    DashboardConversationDetailResponse,
    DashboardConversationResponse,
    DashboardMessageResponse,
    DashboardSummaryResponse,
)
from app.dashboard.service import (
    get_dashboard_conversation,
    get_dashboard_messages,
    get_dashboard_summary,
    list_dashboard_conversations,
)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
)
async def dashboard_summary(
    session: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
):
    """Return high-level metrics for the current tenant."""

    return await get_dashboard_summary(session)


@router.get(
    "/conversations",
    response_model=list[DashboardConversationResponse],
)
async def dashboard_conversations(
    session: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
):
    """Return the current tenant's conversations."""

    return await list_dashboard_conversations(session)


@router.get(
    "/conversations/{conversation_id}",
    response_model=DashboardConversationDetailResponse,
)
async def dashboard_conversation_detail(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
):
    """Return one conversation and its messages."""

    conversation = await get_dashboard_conversation(
        session,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    messages = await get_dashboard_messages(
        session,
        conversation_id,
    )

    return DashboardConversationDetailResponse(
        conversation=DashboardConversationResponse.model_validate(conversation),
        messages=[
            DashboardMessageResponse.model_validate(message)
            for message in messages
        ],
    )