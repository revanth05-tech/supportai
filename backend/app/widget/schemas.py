"""Schemas for the public support widget."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WidgetSessionCreate(BaseModel):
    """Request to create a visitor conversation."""

    model_config = ConfigDict(extra="forbid")

    site_key: str = Field(min_length=1, max_length=200)
    origin_url: str | None = Field(default=None, max_length=2000)


class WidgetSessionResponse(BaseModel):
    """Public session information returned to the widget."""

    conversation_id: UUID
    session_token: str
    status: str
    welcome_message: str

class WidgetMessageResponse(BaseModel):
    """Message returned to the public widget."""

    id: UUID
    role: str
    content: str
    created_at: datetime


class WidgetConversationResponse(BaseModel):
    """Conversation history returned to the public widget."""

    conversation_id: UUID
    status: str
    messages: list[WidgetMessageResponse]