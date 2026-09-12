"""Tenant and agent configuration services."""

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.tenancy.models import Tenant
from app.tenancy.schemas import AgentConfigUpdate

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_secret
from app.tenancy.models import LlmCredential, Tenant, LlmProvider
from app.tenancy.schemas import AgentConfigUpdate, LlmCredentialUpdate

def generate_site_key() -> str:
    """Generate a cryptographically secure public site key."""
    return f"sk_{secrets.token_urlsafe(32)}"


def get_agent_config(tenant: Tenant) -> dict:
    """Return the tenant's stored agent configuration."""
    return {
        "business_name": tenant.agent_config.get("business_name", tenant.name),
        "tone": tenant.agent_config.get("tone", "friendly"),
        "instructions": tenant.agent_config.get("instructions", ""),
        "welcome_message": tenant.agent_config.get(
            "welcome_message",
            "Hi! How can I help you today?",
        ),
    }


async def update_agent_config(
    session: AsyncSession,
    tenant: Tenant,
    payload: AgentConfigUpdate,
) -> Tenant:
    """Update tenant-owned agent configuration."""
    tenant.name = payload.business_name or tenant.name
    tenant.agent_config = {
        "business_name": payload.business_name,
        "tone": payload.tone,
        "instructions": payload.instructions,
        "welcome_message": payload.welcome_message,
    }
    tenant.allowed_origins = payload.allowed_origins

    await session.commit()
    await session.refresh(tenant)

    return tenant


async def rotate_site_key(
    session: AsyncSession,
    tenant: Tenant,
) -> str:
    """Rotate the tenant's public widget site key."""
    tenant.site_key = generate_site_key()

    await session.commit()
    await session.refresh(tenant)

    return tenant.site_key

async def get_llm_credential(
    session: AsyncSession,
    tenant: Tenant,
) -> LlmCredential | None:
    """Return the tenant's encrypted credential record."""
    result = await session.scalar(
        select(LlmCredential).where(LlmCredential.tenant_id == tenant.id)
    )
    return result


async def update_llm_credential(
    session: AsyncSession,
    tenant: Tenant,
    payload: LlmCredentialUpdate,
) -> LlmCredential:
    """Create or replace a tenant's encrypted LLM credential."""

    try:
        provider = LlmProvider(payload.provider)
    except ValueError as exc:
        raise ValueError("Unsupported LLM provider.") from exc

    credential = await get_llm_credential(session, tenant)

    if credential is None:
        credential = LlmCredential(
            tenant_id=tenant.id,
            provider=provider,
            base_url=payload.base_url,
            api_key_encrypted=encrypt_secret(payload.api_key),
        )
        session.add(credential)
    else:
        credential.provider = provider
        credential.base_url = payload.base_url
        credential.api_key_encrypted = encrypt_secret(payload.api_key)

    await session.commit()
    await session.refresh(credential)

    return credential


async def delete_llm_credential(
    session: AsyncSession,
    tenant: Tenant,
) -> bool:
    """Delete the tenant's stored LLM credential."""

    credential = await get_llm_credential(session, tenant)

    if credential is None:
        return False

    await session.delete(credential)
    await session.commit()

    return True