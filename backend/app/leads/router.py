"""API routes for lead management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_tenant, get_db
from app.leads.models import Lead
from app.leads.schemas import LeadResponse, LeadStatusUpdate
from app.leads.service import update_lead_status
from app.tenancy.models import Tenant


router = APIRouter(
    prefix="/api/leads",
    tags=["Leads"],
)


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    session: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await session.scalars(
        select(Lead)
        .where(Lead.tenant_id == tenant.id)
        .order_by(Lead.created_at.desc())
    )

    return list(result.all())


@router.patch("/{lead_id}/status", response_model=LeadResponse)
async def update_status(
    lead_id: UUID,
    payload: LeadStatusUpdate,
    session: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    lead = await session.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == tenant.id,
        )
    )

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found.",
        )

    return await update_lead_status(
        session,
        lead=lead,
        status=payload.status,
    )