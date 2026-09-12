"""Shared SQLAlchemy declarative base for future persistence models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class whose metadata is consumed by Alembic."""
