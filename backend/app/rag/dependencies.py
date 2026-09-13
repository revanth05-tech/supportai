"""Dependencies for constructing the RAG service."""

from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_tenant, get_db
from app.core.crypto import decrypt_secret
from app.rag.llm import LLMClient
from app.rag.openai_compatible import OpenAICompatibleClient
from app.rag.service import RagService
from app.tenancy.models import LlmCredential, Tenant
from sqlalchemy import select


def get_embedder_model_dir() -> str:
    """Return the local embedding model directory."""

    return str(
        Path(__file__).resolve().parents[2]
        / "models"
        / "all-MiniLM-L6-v2"
    )


def create_embedder():
    """Create the local ONNX embedding model."""

    from app.knowledge.onnx_embedder import OnnxEmbedder

    return OnnxEmbedder(get_embedder_model_dir())


async def get_tenant_llm_client(
    session: AsyncSession,
    tenant: Tenant,
) -> LLMClient:
    """Create an LLM client from the tenant's encrypted credential."""

    credential = await session.scalar(
        select(LlmCredential).where(
            LlmCredential.tenant_id == tenant.id
        )
    )

    if credential is None:
        raise RuntimeError(
            "No LLM provider is configured for this tenant."
        )

    api_key = decrypt_secret(
        credential.api_key_encrypted
    )

    base_url = credential.base_url

    if not base_url:
        if credential.provider.value == "OpenRouter":
            base_url = "https://openrouter.ai/api/v1"
        elif credential.provider.value == "OpenAI":
            base_url = "https://api.openai.com/v1"
        else:
            raise RuntimeError(
                "A base URL is required for this LLM provider."
            )

    model = "openai/gpt-4o-mini"

    return OpenAICompatibleClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


async def get_rag_service(
    session: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RagService:
    """Construct a tenant-aware RAG service."""

    embedder = create_embedder()

    llm_client = await get_tenant_llm_client(
        session,
        tenant,
    )

    return RagService(
        embedder=embedder,
        llm_client=llm_client,
    )