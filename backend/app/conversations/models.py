"""Conversation and audit-message persistence models."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import utc_now

if TYPE_CHECKING:
    from app.leads.models import Lead
    from app.tenancy.models import Tenant


class ConversationStatus(str, Enum):
    ACTIVE = "Active"
    HANDED_OFF = "HandedOff"
    CLOSED = "Closed"


class MessageRole(str, Enum):
    USER = "User"
    ASSISTANT = "Assistant"
    SYSTEM = "System"


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_tenant_id_status_last_message_at", "tenant_id", "status", "last_message_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    session_token: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(SqlEnum(ConversationStatus, native_enum=False, values_callable=lambda e: [x.value for x in e]), default=ConversationStatus.ACTIVE, nullable=False)
    origin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    lead: Mapped["Lead | None"] = relationship(back_populates="conversation", cascade="all, delete-orphan", uselist=False)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_id_created_at", "conversation_id", "created_at"), Index("ix_messages_tenant_id", "tenant_id"))

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="NO ACTION"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(SqlEnum(MessageRole, native_enum=False, values_callable=lambda e: [x.value for x in e]), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    retrieved_chunk_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    matched_titles: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    top_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    was_grounded: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    tenant: Mapped["Tenant"] = relationship(back_populates="messages")
