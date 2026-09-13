"""Dependencies for authenticating public widget requests."""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_db
from app.common.tenant_context import set_authenticated_identity, system_access
from app.tenancy.models import Tenant


async def get_widget_tenant(
    site_key: str,
    origin: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    Resolve a tenant from the public widget site key.

    Site-key lookup is intentionally performed with system access because
    there is no authenticated tenant context yet. Once the tenant is resolved,
    the request receives that tenant's identity and normal tenant isolation
    applies to subsequent database operations.
    """

    with system_access():
        tenant = await session.scalar(
            select(Tenant).where(Tenant.site_key == site_key)
        )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid site key.",
        )

    allowed_origins = tenant.allowed_origins or []

    if allowed_origins and (origin is None or origin not in allowed_origins):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin is not allowed.",
        )

    set_authenticated_identity(
        tenant.owner_user_id,
        tenant.id,
    )

    return tenant