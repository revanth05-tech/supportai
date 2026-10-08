"""Tenant and global usage quota helpers."""
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


TENANT_DAILY_MESSAGE_LIMIT = 200
GLOBAL_DAILY_FREE_CALL_LIMIT = 45


async def consume_tenant_message(
    session: AsyncSession,
    *,
    tenant_id,
    usage_date: date | None = None,
    limit: int = TENANT_DAILY_MESSAGE_LIMIT,
) -> bool:
    """Atomically reserve one tenant message for the current usage day."""

    usage_date = usage_date or datetime.now(timezone.utc).date()

    result = await session.execute(
        text(
            """
            INSERT INTO tenant_daily_usage (
                tenant_id,
                usage_date,
                message_count
            )
            VALUES (
                :tenant_id,
                :usage_date,
                1
            )
            ON CONFLICT (tenant_id, usage_date)
            DO UPDATE
            SET message_count = tenant_daily_usage.message_count + 1
            WHERE tenant_daily_usage.message_count < :limit
            RETURNING message_count
            """
        ),
        {
            "tenant_id": tenant_id,
            "usage_date": usage_date,
            "limit": limit,
        },
    )

    row = result.first()

    if row is None:
        return False

    return True

async def consume_global_free_call(
    session: AsyncSession,
    *,
    usage_date: date | None = None,
    limit: int = GLOBAL_DAILY_FREE_CALL_LIMIT,
) -> bool:
    """Atomically reserve one shared free-provider call for the current UTC day."""

    usage_date = usage_date or datetime.now(timezone.utc).date()

    result = await session.execute(
        text(
            """
            INSERT INTO global_daily_usage (
                usage_date,
                free_call_count
            )
            VALUES (
                :usage_date,
                1
            )
            ON CONFLICT (usage_date)
            DO UPDATE
            SET free_call_count = global_daily_usage.free_call_count + 1
            WHERE global_daily_usage.free_call_count < :limit
            RETURNING free_call_count
            """
        ),
        {
            "usage_date": usage_date,
            "limit": limit,
        },
    )

    row = result.first()

    if row is None:
        return False

    return True