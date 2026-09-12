"""Reusable FastAPI dependencies."""

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.tenant_context import get_current_tenant_id, set_authenticated_identity, system_access
from app.db.session import AsyncSessionLocal
from app.identity.jwt_service import InvalidAccessTokenError, decode_access_token, is_demo_claim
from app.identity.models import User
from app.tenancy.models import Tenant


bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield one transaction-capable async database session per request."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate the bearer token and establish request-local tenant identity."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = str(claims["sub"])
        claim_email = str(claims["email"])
        tenant_id = UUID(str(claims["tenantId"]))
    except (InvalidAccessTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token.") from exc

    user = await session.get(User, user_id)
    with system_access():
        tenant = await session.scalar(select(Tenant).where(Tenant.owner_user_id == user_id))
    if user is None or tenant is None or tenant.id != tenant_id or user.email != claim_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token identity.")
    set_authenticated_identity(user.id, tenant.id)
    return user


async def require_authenticated_user(user: User = Depends(get_current_user)) -> User:
    return user


async def get_current_tenant(
    _: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> Tenant:
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant is unavailable.")
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant is unavailable.")
    return tenant


def is_demo_user_claims(claims: dict[str, object]) -> bool:
    """Reusable future demo guard without inventing a demo account."""
    return is_demo_claim(claims)
