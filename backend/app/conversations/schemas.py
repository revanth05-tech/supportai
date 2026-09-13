"""Schemas for visitor conversations and messages."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    """Public widget request to start a conversation."""

    model_config = ConfigDict(extra="forbid")

    origin_url: str | None = Field(default=None, max_length=2000)


class ConversationResponse(BaseModel):
    """Conversation information returned to the widget."""

    id: UUID
    session_token: str
    status: str
    origin_url: str | None
    started_at: datetime
    last_message_at: datetime


class MessageResponse(BaseModel):
    """Persisted conversation message."""

    id: UUID
    role: str
    content: str
    retrieved_chunk_ids: list[str] | None
    matched_titles: list[str] | None
    top_similarity: float | None
    model_used: str | None
    was_grounded: bool | None
    latency_ms: int | None
    created_at: datetime