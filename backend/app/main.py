"""FastAPI application entry point."""

from fastapi import FastAPI

from app.common.middleware import register_middleware
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.identity.router import router as identity_router
from app.tenancy.router import router as tenancy_router
from app.knowledge.router import router as knowledge_router
from app.rag.router import router as rag_router
from app.widget.router import router as widget_router
from app.leads.router import router as leads_router

def create_app() -> FastAPI:
    """Create the application without importing domain implementations."""
    configure_logging(settings)
    application = FastAPI(title=settings.app_name, debug=settings.debug)
    register_middleware(application)
    register_exception_handlers(application)
    application.include_router(identity_router)
    application.include_router(tenancy_router)
    application.include_router(knowledge_router)
    application.include_router(rag_router)
    application.include_router(widget_router)
    application.include_router(leads_router)
    @application.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
