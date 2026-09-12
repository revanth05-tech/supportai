"""Application exception seam and minimal HTTP error translation."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApplicationError(Exception):
    """Base exception for future domain errors."""

    status_code = 400
    title = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.title
        super().__init__(self.detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Register the shared handler; domain-specific errors come later."""

    @app.exception_handler(ApplicationError)
    async def application_error_handler(_: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"title": exc.title, "detail": exc.detail})
