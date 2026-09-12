"""Tenant and usage persistence models."""

import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, LargeBinary, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import utc_now

if TYPE_CHECKING:
    from app.conversations.models import Conversation, Message
    from app.identity.models import User
    from app.knowledge.models import Chunk, KnowledgeItem
    from app.leads.models import Lead


class LlmProvider(str, Enum):
    OPENROUTER = "OpenRouter"
    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"
    OTHER = "Other"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Retain the original ASP.NET Identity text key for this ownership FK.
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    site_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    allowed_origins: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    agent_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=utc_now)

    owner: Mapped["User"] = relationship(back_populates="tenant")
    llm_credential: Mapped["LlmCredential | None"] = relationship(back_populates="tenant", cascade="all, delete-orphan", uselist=False)
    daily_usage: Mapped[list["TenantDailyUsage"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    knowledge_items: Mapped[list["KnowledgeItem"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="tenant", passive_deletes=True)
    messages: Mapped[list["Message"]] = relationship(back_populates="tenant", passive_deletes=True)
    leads: Mapped[list["Lead"]] = relationship(back_populates="tenant", passive_deletes=True)


class LlmCredential(Base):
    __tablename__ = "llm_credentials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    provider: Mapped[LlmProvider] = mapped_column(SqlEnum(LlmProvider, native_enum=False, values_callable=lambda e: [x.value for x in e]), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=utc_now)

    tenant: Mapped[Tenant] = relationship(back_populates="llm_credential")


class TenantDailyUsage(Base):
    __tablename__ = "tenant_daily_usage"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="daily_usage")


class GlobalDailyUsage(Base):
    __tablename__ = "global_daily_usage"

    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    free_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    operator_alert_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DataProtectionKeys(Base):
    __tablename__ = "data_protection_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    friendly_name: Mapped[str | None] = mapped_column(String, nullable=True)
    xml: Mapped[str | None] = mapped_column(String, nullable=True)
