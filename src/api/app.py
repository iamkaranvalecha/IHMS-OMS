"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import ObservabilityMiddleware
from src.api.routes import catalog_router, health_router, sessions_router
from src.catalog.provider import JsonCatalogProvider
from src.checkout.service import CheckoutService
from src.gateway.factory import gateway_clients
from src.session.store import InMemorySessionStore
from src.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire gateway clients, catalog, and session store."""
    settings: Settings = app.state.settings
    catalog = JsonCatalogProvider(settings.catalog_path)
    sessions = InMemorySessionStore()

    async with gateway_clients(settings) as (ihms, ecops):
        app.state.checkout_service = CheckoutService(
            catalog=catalog,
            sessions=sessions,
            ihms=ihms,
            ecops=ecops,
        )
        yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the orchestrator API application."""
    resolved = settings or get_settings()
    app = FastAPI(
        title="Checkout Orchestrator",
        description="BFF and saga layer for KB-IHMS + EC-OPS checkout integration",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.add_middleware(ObservabilityMiddleware)
    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(sessions_router)
    return app
