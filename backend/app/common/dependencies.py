"""Reusable FastAPI dependencies."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield one transaction-capable async database session per request."""
    async with AsyncSessionLocal() as session:
        yield session
