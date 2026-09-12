"""Small, structured logging setup shared by the FastAPI application."""

import json
import logging
from datetime import datetime, timezone

from app.core.config import Settings


class JsonFormatter(logging.Formatter):
    """Render standard library log records as compact JSON."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
             "logger": record.name, "message": record.getMessage()},
            default=str,
        )


def configure_logging(settings: Settings) -> None:
    """Configure root logging once, avoiding duplicate handlers on reload."""
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if settings.debug else logging.INFO)
