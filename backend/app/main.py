"""FastAPI application entrypoint for the BitonX backend foundation."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create the backend application without registering business API routes."""
    settings = get_settings()
    configure_logging(settings.log_level)

    return FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )


app = create_app()

