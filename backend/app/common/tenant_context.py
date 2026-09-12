"""Request/task-local tenant identity and explicit system-access scopes."""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator
from uuid import UUID


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID | None = None
    user_id: str | None = None
    system_access: bool = False


class TenantContextMissingError(RuntimeError):
    """Raised when tenant-owned data is accessed without an explicit scope."""


class TenantAccessViolationError(RuntimeError):
    """Raised when a request attempts to write another tenant's data."""


_context: ContextVar[TenantContext] = ContextVar("tenant_context", default=TenantContext())


def get_tenant_context() -> TenantContext:
    return _context.get()


def get_current_tenant_id() -> UUID | None:
    return _context.get().tenant_id


def set_current_tenant_id(tenant_id: UUID | None) -> Token[TenantContext]:
    current = _context.get()
    return _context.set(TenantContext(tenant_id=tenant_id, user_id=current.user_id, system_access=current.system_access))


def set_authenticated_identity(user_id: str, tenant_id: UUID) -> Token[TenantContext]:
    return _context.set(TenantContext(tenant_id=tenant_id, user_id=user_id))


def reset_current_tenant_id(token: Token[TenantContext]) -> None:
    _context.reset(token)


@contextmanager
def system_access() -> Iterator[None]:
    """Explicitly allow unscoped system operations such as registration/seeding."""
    token = _context.set(TenantContext(system_access=True))
    try:
        yield
    finally:
        _context.reset(token)
