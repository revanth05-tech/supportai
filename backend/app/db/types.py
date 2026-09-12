"""Shared PostgreSQL persistence helpers."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return an aware UTC timestamp for ORM-side defaults."""
    return datetime.now(UTC)
