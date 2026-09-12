"""Tenant agent configuration and site-key endpoints."""

from fastapi import APIRouter, Depends,HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_tenant, get_db
from app.tenancy.models import Tenant
from app.tenancy.schemas import (
    AgentConfigResponse,
    AgentConfigUpdate,
    LlmCredentialResponse,
    LlmCredentialUpdate,
    SiteKeyResponse,
)
from app.tenancy.service import (
    delete_llm_credential,
    get_agent_config,
    get_llm_credential,
    rotate_site_key,
    update_agent_config,
    update_llm_credential,
)

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.get("", response_model=AgentConfigResponse)
async def get_agent(
    tenant: Tenant = Depends(get_current_tenant),
) -> AgentConfigResponse:
    config = get_agent_config(tenant)

    return AgentConfigResponse(
        tenant_id=tenant.id,
        business_name=config["business_name"],
        tone=config["tone"],
        instructions=config["instructions"],
        welcome_message=config["welcome_message"],
        allowed_origins=tenant.allowed_origins,
    )


@router.put("", response_model=AgentConfigResponse)
async def update_agent(
    payload: AgentConfigUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> AgentConfigResponse:
    tenant = await update_agent_config(session, tenant, payload)
    config = get_agent_config(tenant)

    return AgentConfigResponse(
        tenant_id=tenant.id,
        business_name=config["business_name"],
        tone=config["tone"],
        instructions=config["instructions"],
        welcome_message=config["welcome_message"],
        allowed_origins=tenant.allowed_origins,
    )


@router.post("/rotate-site-key", response_model=SiteKeyResponse)
async def rotate_agent_site_key(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> SiteKeyResponse:
    site_key = await rotate_site_key(session, tenant)

    return SiteKeyResponse(site_key=site_key)

@router.get("/llm", response_model=LlmCredentialResponse)
async def get_llm(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> LlmCredentialResponse:
    credential = await get_llm_credential(session, tenant)

    if credential is None:
        return LlmCredentialResponse(
            provider="",
            base_url=None,
            configured=False,
        )

    return LlmCredentialResponse(
        provider=credential.provider.value,
        base_url=credential.base_url,
        configured=True,
    )


@router.put("/llm", response_model=LlmCredentialResponse)
async def update_llm(
    payload: LlmCredentialUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> LlmCredentialResponse:
    try:
        credential = await update_llm_credential(session, tenant, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return LlmCredentialResponse(
        provider=credential.provider.value,
        base_url=credential.base_url,
        configured=True,
    )


@router.delete("/llm", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> None:
    await delete_llm_credential(session, tenant)