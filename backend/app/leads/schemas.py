"""Schemas for lead capture and management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.leads.models import LeadReason, LeadStatus


class LeadCreate(BaseModel):
    """Create a lead from a support conversation."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    reason: LeadReason
    stumping_question: str | None = Field(default=None, max_length=1000)
    visitor_message: str | None = Field(default=None, max_length=1000)


class LeadContactUpdate(BaseModel):
    """Capture visitor contact information for an existing lead."""

    model_config = ConfigDict(extra="forbid")

    contact_name: str = Field(min_length=1, max_length=200)
    contact_email: EmailStr
    contact_phone: str | None = Field(default=None, max_length=50)
    visitor_message: str | None = Field(default=None, max_length=1000)


class LeadStatusUpdate(BaseModel):
    """Update the lifecycle status of a lead."""

    model_config = ConfigDict(extra="forbid")

    status: LeadStatus


class LeadResponse(BaseModel):
    """Public representation of a lead."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    conversation_id: UUID
    reason: LeadReason
    stumping_question: str | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    visitor_message: str | None
    status: LeadStatus
    created_at: datetime
    updated_at: datetime | None