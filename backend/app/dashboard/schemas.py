"""Schemas for owner dashboard responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.conversations.models import ConversationStatus, MessageRole


class DashboardSummaryResponse(BaseModel):
    """High-level metrics for the tenant dashboard."""

    total_conversations: int
    active_conversations: int
    handed_off_conversations: int
    total_leads: int
    new_leads: int


class DashboardConversationResponse(BaseModel):
    """Conversation summary shown in the owner dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ConversationStatus
    origin_url: str | None
    started_at: datetime
    last_message_at: datetime


class DashboardMessageResponse(BaseModel):
    """Message details shown when an owner opens a conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    retrieved_chunk_ids: list[str] | None
    matched_titles: list[str] | None
    top_similarity: float | None
    model_used: str | None
    was_grounded: bool | None
    latency_ms: int | None
    created_at: datetime


class DashboardConversationDetailResponse(BaseModel):
    """Conversation plus its complete message history."""

    conversation: DashboardConversationResponse
    messages: list[DashboardMessageResponse]