"""Dependencies for constructing the RAG service."""

from pathlib import Path

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_tenant, get_db
from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.rag.llm import LLMClient
from app.rag.openai_compatible import OpenAICompatibleClient
from app.rag.service import RagService
from app.tenancy.models import LlmCredential, Tenant


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
    """Create the appropriate LLM client for the tenant."""

    credential = await session.scalar(
        select(LlmCredential).where(
            LlmCredential.tenant_id == tenant.id
        )
    )

    # Tenant-specific BYOK credential.
    if credential is not None:
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
            uses_shared_quota=False,
        )

    # Fall back to the application's shared provider.
    if not settings.shared_llm_api_key:
        raise RuntimeError(
            "No tenant LLM credential is configured and "
            "the shared LLM provider is unavailable."
        )

    return OpenAICompatibleClient(
        api_key=settings.shared_llm_api_key,
        base_url=settings.shared_llm_base_url,
        model=settings.shared_llm_model,
        uses_shared_quota=True,
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