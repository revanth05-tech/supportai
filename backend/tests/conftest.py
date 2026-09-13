import pytest
from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.tenant_context import system_access
from app.db.session import AsyncSessionLocal
from app.identity.models import User
from app.tenancy.models import Tenant


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def existing_tenant(
    db_session: AsyncSession,
) -> AsyncGenerator[Tenant, None]:
    user_id = str(uuid4())

    user = User(
        id=user_id,
        email=f"widget-test-{user_id}@example.com",
        display_name="Widget Test User",
        password_hash="test-password-hash",
    )

    tenant = Tenant(
        owner_user_id=user_id,
        name="Widget Test Tenant",
        site_key=f"widget-test-{user_id}",
        allowed_origins=[],
        agent_config={
            "welcome_message": "Hi! How can I help you today?"
        },
    )

    with system_access():
        db_session.add(user)
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)

    try:
        yield tenant
    finally:
        with system_access():
            await db_session.delete(tenant)
            await db_session.delete(user)
            await db_session.commit()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"