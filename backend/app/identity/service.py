"""Transactional authentication and refresh-token services."""

import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.tenant_context import system_access
from app.core.security import hash_password, hash_token, verify_password
from app.core.config import settings
from app.db.types import utc_now
from app.identity.jwt_service import create_access_token
from app.identity.models import RefreshToken, User
from app.tenancy.models import Tenant


class AuthenticationError(ValueError):
    pass


class DuplicateEmailError(ValueError):
    pass


def hash_refresh_token(raw_token: str) -> str:
    return hash_token(raw_token)


def _new_raw_refresh_token() -> str:
    return secrets.token_urlsafe(32)


async def _new_site_key(session: AsyncSession) -> str:
    while True:
        candidate = f"wsk_{secrets.token_urlsafe(24)}"
        existing = await session.scalar(select(Tenant.id).where(Tenant.site_key == candidate))
        if existing is None:
            return candidate


async def create_refresh_token(session: AsyncSession, user_id: str) -> tuple[str, RefreshToken]:
    raw_token = _new_raw_refresh_token()
    record = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=utc_now() + timedelta(days=settings.refresh_token_expire_days),
    )
    session.add(record)
    return raw_token, record


async def register_user(
    session: AsyncSession, *, email: str, password: str, display_name: str | None, tenant_name: str
) -> tuple[User, Tenant, str, str]:
    """Atomically create the v1 user, their sole tenant, and both token types."""
    normalized_email = email.lower()
    async with session.begin():
        with system_access():
            if await session.scalar(select(User.id).where(User.email == normalized_email)) is not None:
                raise DuplicateEmailError("An account with this email already exists.")
            user = User(id=str(uuid.uuid4()), email=normalized_email, display_name=display_name, password_hash=hash_password(password))
            tenant = Tenant(
                id=uuid.uuid4(), owner_user_id=user.id, name=tenant_name,
                site_key=await _new_site_key(session), allowed_origins=[], agent_config={},
            )
            session.add_all([user, tenant])
            raw_refresh, _ = await create_refresh_token(session, user.id)
    access_token = create_access_token(user_id=user.id, email=user.email, tenant_id=str(tenant.id))
    return user, tenant, access_token, raw_refresh


async def login_user(session: AsyncSession, *, email: str, password: str) -> tuple[User, Tenant, str, str]:
    async with session.begin():
        with system_access():
            user = await session.scalar(select(User).where(User.email == email.lower()))
            if user is None or not verify_password(password, user.password_hash):
                raise AuthenticationError("Invalid email or password.")
            tenant = await session.scalar(select(Tenant).where(Tenant.owner_user_id == user.id))
            if tenant is None:
                raise AuthenticationError("Account tenant is unavailable.")
            raw_refresh, _ = await create_refresh_token(session, user.id)
    access_token = create_access_token(user_id=user.id, email=user.email, tenant_id=str(tenant.id))
    return user, tenant, access_token, raw_refresh


async def rotate_refresh_token(session: AsyncSession, raw_token: str) -> tuple[User, Tenant, str, str]:
    """Atomically revoke a refresh token and create its single replacement."""
    async with session.begin():
        token_hash = hash_refresh_token(raw_token)
        record = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update())
        if record is None or record.revoked_at is not None or record.expires_at <= utc_now():
            raise AuthenticationError("Refresh token is invalid, expired, or already used.")
        with system_access():
            user = await session.get(User, record.user_id)
            tenant = await session.scalar(select(Tenant).where(Tenant.owner_user_id == record.user_id))
            if user is None or tenant is None:
                raise AuthenticationError("Refresh token account is unavailable.")
            replacement_raw, replacement = await create_refresh_token(session, user.id)
            record.revoked_at = utc_now()
            record.replaced_by_token_id = replacement.id
    access_token = create_access_token(user_id=user.id, email=user.email, tenant_id=str(tenant.id))
    return user, tenant, access_token, replacement_raw


async def revoke_refresh_token(session: AsyncSession, raw_token: str) -> None:
    async with session.begin():
        record = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token)).with_for_update())
        if record is not None and record.revoked_at is None:
            record.revoked_at = utc_now()
