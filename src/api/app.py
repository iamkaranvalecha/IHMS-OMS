"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import ObservabilityMiddleware
from src.api.routes import health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — gateway client pools wired in Phase 2."""
    yield


def create_app() -> FastAPI:
    """Build the orchestrator API application."""
    app = FastAPI(
        title="Checkout Orchestrator",
        description="BFF and saga layer for KB-IHMS + EC-OPS checkout integration",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(ObservabilityMiddleware)
    app.include_router(health_router)
    return app
