"""Reserved middleware registration seam for later auth and tenant resolution."""

from fastapi import FastAPI, Request

from app.common.tenant_context import reset_current_tenant_id, set_current_tenant_id


def register_middleware(app: FastAPI) -> None:
    """Reset request-local context even when a dependency or handler raises."""
    @app.middleware("http")
    async def tenant_context_lifecycle(_: Request, call_next: object) -> object:
        token = set_current_tenant_id(None)
        try:
            return await call_next(_)  # type: ignore[operator]
        finally:
            reset_current_tenant_id(token)
