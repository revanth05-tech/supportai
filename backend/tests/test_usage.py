"""Tests for tenant and global usage quotas."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tenancy.usage import (
    consume_global_free_call,
    consume_tenant_message,
)


@pytest.mark.anyio
async def test_consume_tenant_message_allows_request():
    session = AsyncMock()

    result = MagicMock()
    result.first.return_value = (1,)
    session.execute.return_value = result

    allowed = await consume_tenant_message(
        session,
        tenant_id="tenant-1",
        usage_date=date(2026, 9, 27),
    )

    assert allowed is True
    session.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_consume_tenant_message_rejects_when_limit_reached():
    session = AsyncMock()

    result = MagicMock()
    result.first.return_value = None
    session.execute.return_value = result

    allowed = await consume_tenant_message(
        session,
        tenant_id="tenant-1",
        usage_date=date(2026, 9, 27),
        limit=200,
    )

    assert allowed is False
    session.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_consume_global_free_call_allows_request():
    session = AsyncMock()

    result = MagicMock()
    result.first.return_value = (1,)
    session.execute.return_value = result

    allowed = await consume_global_free_call(
        session,
        usage_date=date(2026, 9, 27),
    )

    assert allowed is True
    session.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_consume_global_free_call_rejects_when_limit_reached():
    session = AsyncMock()

    result = MagicMock()
    result.first.return_value = None
    session.execute.return_value = result

    allowed = await consume_global_free_call(
        session,
        usage_date=date(2026, 9, 27),
        limit=45,
    )

    assert allowed is False
    session.execute.assert_awaited_once()