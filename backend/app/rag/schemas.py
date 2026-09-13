"""Schemas for RAG chat requests."""

from pydantic import BaseModel, ConfigDict, Field


class ChatHistoryMessage(BaseModel):
    """A previous conversation message."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=1, max_length=4000)


class RagChatRequest(BaseModel):
    """Request body for a RAG chat turn."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatHistoryMessage] = Field(
        default_factory=list,
        max_length=10,
    )