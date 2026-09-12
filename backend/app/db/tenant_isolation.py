"""Mandatory tenant scoping and stamping hooks for SQLAlchemy ORM sessions."""

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.common.tenant_context import TenantAccessViolationError, TenantContextMissingError, get_tenant_context
from app.conversations.models import Conversation, Message
from app.knowledge.models import Chunk, KnowledgeItem
from app.leads.models import Lead
from app.tenancy.models import LlmCredential, Tenant, TenantDailyUsage


TENANT_OWNED_MODELS = (Tenant, LlmCredential, TenantDailyUsage, KnowledgeItem, Chunk, Conversation, Message, Lead)


def _criterion(model: type, tenant_id: object) -> object:
    return model.id == tenant_id if model is Tenant else model.tenant_id == tenant_id


def _loader_criterion(model: type, tenant_id: object) -> object:
    """Create a closure SQLAlchemy can bind/cache safely per tenant value."""
    return lambda cls: _criterion(model, tenant_id)


@event.listens_for(Session, "do_orm_execute")
def enforce_tenant_scope(orm_execute_state: object) -> None:
    """Scope every ORM select/bulk write for tenant-owned mapped classes."""
    state = orm_execute_state
    if not (state.is_select or state.is_update or state.is_delete):
        return
    context = get_tenant_context()
    mapper = state.bind_mapper
    model = mapper.class_ if mapper is not None else None
    statement = state.statement

    if context.system_access:
        return
    if context.tenant_id is None:
        if model in TENANT_OWNED_MODELS:
            raise TenantContextMissingError("Tenant-owned data requires a tenant context or explicit system access.")
        if state.is_select and any(
            description.get("entity") in TENANT_OWNED_MODELS
            for description in getattr(statement, "column_descriptions", ())
        ):
            raise TenantContextMissingError("Tenant-owned data requires a tenant context or explicit system access.")
        return
    if state.is_select:
        for scoped_model in TENANT_OWNED_MODELS:
            statement = statement.options(
                with_loader_criteria(scoped_model, _loader_criterion(scoped_model, context.tenant_id), include_aliases=True)
            )
        state.statement = statement
    elif model in TENANT_OWNED_MODELS:
        state.statement = statement.where(_criterion(model, context.tenant_id))


@event.listens_for(Session, "before_flush")
def stamp_and_validate_tenant_rows(session: Session, _: object, __: object) -> None:
    """Stamp new tenant rows and reject cross-tenant writes from normal scopes."""
    context = get_tenant_context()
    for instance in session.new.union(session.dirty):
        if not isinstance(instance, TENANT_OWNED_MODELS):
            continue
        if context.system_access:
            continue
        if context.tenant_id is None:
            raise TenantContextMissingError("Creating tenant-owned data requires a tenant context or explicit system access.")
        if isinstance(instance, Tenant):
            if instance.id is not None and instance.id != context.tenant_id:
                raise TenantAccessViolationError("Cannot modify a different tenant.")
            instance.id = context.tenant_id
        elif instance.tenant_id is None:
            instance.tenant_id = context.tenant_id
        elif instance.tenant_id != context.tenant_id:
            raise TenantAccessViolationError("Cannot create data for a different tenant.")
