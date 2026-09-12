"""Request-local tenant-context seam; resolution and enforcement come later."""

from contextvars import ContextVar, Token
from uuid import UUID


_tenant_id: ContextVar[UUID | None] = ContextVar("tenant_id", default=None)


def get_current_tenant_id() -> UUID | None:
    return _tenant_id.get()


def set_current_tenant_id(tenant_id: UUID | None) -> Token[UUID | None]:
    return _tenant_id.set(tenant_id)


def reset_current_tenant_id(token: Token[UUID | None]) -> None:
    _tenant_id.reset(token)
