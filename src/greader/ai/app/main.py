"""Composition root for the standalone AI HTTP application."""

import os

from fastapi import FastAPI

from greader.ai.app.repository import VectorRepository
from greader.ai.app.routes import router as vector_router
from greader.ai.app.service import VectorService
from greader.ai.database.vector_repository import create_postgres_repository


def create_app(*, repository: VectorRepository) -> FastAPI:
    """Build an isolated AI application with a supplied repository."""
    application = FastAPI(
        title="GReader AI",
        description="Vector storage and similarity search for GReader.",
        version="0.1.0",
    )
    application.state.vector_service = VectorService(repository)
    application.include_router(vector_router)
    return application


def create_production_app() -> FastAPI:
    """Build the production AI application without opening a database connection."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url is None:
        raise RuntimeError("DATABASE_URL is required")

    repository = create_postgres_repository(database_url)
    return create_app(repository=repository)
