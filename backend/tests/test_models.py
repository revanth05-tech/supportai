from app.conversations.models import Conversation, Message
from app.db.base import Base
from app.identity.models import RefreshToken, User
from app.knowledge.models import Chunk, KnowledgeItem
from app.leads.models import Lead
from app.tenancy.models import DataProtectionKeys, GlobalDailyUsage, LlmCredential, Tenant, TenantDailyUsage


def test_metadata_contains_domain_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users", "refresh_tokens", "tenants", "llm_credentials", "tenant_daily_usage",
        "global_daily_usage", "data_protection_keys", "knowledge_items", "chunks",
        "conversations", "messages", "leads",
    }


def test_chunk_embedding_is_384_dimension_vector() -> None:
    embedding_type = Chunk.__table__.c.embedding.type
    assert embedding_type.dim == 384


def test_key_constraints_and_indexes_are_declared() -> None:
    assert Tenant.__table__.c.owner_user_id.unique
    assert Tenant.__table__.c.site_key.unique
    assert LlmCredential.__table__.c.tenant_id.unique
    assert Lead.__table__.c.conversation_id.unique
    assert {index.name for index in Chunk.__table__.indexes} >= {
        "ix_chunks_tenant_id", "ix_chunks_knowledge_item_id", "ix_chunks_embedding_hnsw"
    }
    assert {index.name for index in Message.__table__.indexes} >= {
        "ix_messages_conversation_id_created_at", "ix_messages_tenant_id"
    }
    assert {column.name for column in TenantDailyUsage.__table__.primary_key.columns} == {"tenant_id", "usage_date"}
