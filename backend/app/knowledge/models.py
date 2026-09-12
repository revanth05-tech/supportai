"""Knowledge persistence models without chunking or retrieval behavior."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import utc_now

if TYPE_CHECKING:
    from app.tenancy.models import Tenant


class KnowledgeItemType(str, Enum):
    FAQ = "Faq"
    SERVICE = "Service"
    POLICY = "Policy"
    BUSINESS_PROFILE = "BusinessProfile"


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    __table_args__ = (Index("ix_knowledge_items_tenant_id_item_type", "tenant_id", "item_type"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    item_type: Mapped[KnowledgeItemType] = mapped_column(SqlEnum(KnowledgeItemType, native_enum=False, values_callable=lambda e: [x.value for x in e]), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=utc_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="knowledge_items")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="knowledge_item", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_tenant_id", "tenant_id"),
        Index("ix_chunks_knowledge_item_id", "knowledge_item_id"),
        Index("ix_chunks_embedding_hnsw", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="NO ACTION"), nullable=False)
    knowledge_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="chunks")
    knowledge_item: Mapped[KnowledgeItem] = relationship(back_populates="chunks")
