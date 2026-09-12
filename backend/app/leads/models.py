"""Lead persistence models without lead-capture behavior."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import utc_now

if TYPE_CHECKING:
    from app.conversations.models import Conversation
    from app.tenancy.models import Tenant


class LeadReason(str, Enum):
    EXPLICIT = "Explicit"
    NO_GROUNDING = "NoGrounding"
    UNRESOLVED = "Unresolved"
    QUOTA_OVERFLOW = "QuotaOverflow"


class LeadStatus(str, Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    CLOSED = "Closed"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_tenant_id_status", "tenant_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="NO ACTION"), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False)
    reason: Mapped[LeadReason] = mapped_column(SqlEnum(LeadReason, native_enum=False, values_callable=lambda e: [x.value for x in e]), nullable=False)
    stumping_question: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    visitor_message: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[LeadStatus] = mapped_column(SqlEnum(LeadStatus, native_enum=False, values_callable=lambda e: [x.value for x in e]), default=LeadStatus.NEW, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=utc_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="leads")
    conversation: Mapped["Conversation"] = relationship(back_populates="lead")
