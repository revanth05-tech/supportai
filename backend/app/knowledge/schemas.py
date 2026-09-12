"""Knowledge base API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeItemCreate(BaseModel):
    """Create a typed knowledge item."""

    model_config = ConfigDict(extra="forbid")

    item_type: str = Field(min_length=1, max_length=50)
    payload: dict = Field(default_factory=dict)


class KnowledgeItemUpdate(BaseModel):
    """Update a typed knowledge item."""

    model_config = ConfigDict(extra="forbid")

    item_type: str = Field(min_length=1, max_length=50)
    payload: dict = Field(default_factory=dict)


class KnowledgeItemResponse(BaseModel):
    """Knowledge item returned by the API."""

    id: UUID
    item_type: str
    payload: dict