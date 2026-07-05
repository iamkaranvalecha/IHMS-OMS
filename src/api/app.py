"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.api.middleware import ObservabilityMiddleware
from src.api.routes import catalog_router, health_router, sessions_router
from src.catalog.ecops_mapping import EcopsMapping
from src.catalog.ihms_cache import IhmsCatalogAdapter, IhmsCatalogCache
from src.catalog.provider import JsonCatalogProvider
from src.checkout.service import CheckoutService
from src.gateway.factory import gateway_clients
from src.observability.logging import configure_logging
from src.session.store import InMemorySessionStore
from src.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire gateway clients, catalog, and session store."""
    settings: Settings = app.state.settings
    ecops_mapping = EcopsMapping.from_path(settings.ecops_mapping_path)
    ihms_catalog_cache: IhmsCatalogCache | None = None
    if settings.catalog_source == "ihms":
        ihms_catalog_cache = IhmsCatalogCache()
        catalog = IhmsCatalogAdapter(ihms_catalog_cache)
    else:
        catalog = JsonCatalogProvider(settings.catalog_path)
    sessions = InMemorySessionStore()

    async with gateway_clients(settings) as (ihms, ecops):
        app.state.checkout_service = CheckoutService.create(
            catalog=catalog,
            sessions=sessions,
            ihms=ihms,
            ecops=ecops,
            ihms_catalog_cache=ihms_catalog_cache,
            ecops_mapping=ecops_mapping,
        )
        logger.info(
            "checkout orchestrator ready: catalog_source=%s ihms_base_url=%s ecops_base_url=%s",
            settings.catalog_source,
            settings.ihms_base_url,
            settings.ecops_base_url,
        )
        yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the orchestrator API application."""
    resolved = settings or get_settings()
    configure_logging(level=resolved.log_level, json_format=resolved.log_json)

    app = FastAPI(
        title="Checkout Orchestrator",
        description="BFF and saga layer for KB-IHMS + EC-OPS checkout integration",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ObservabilityMiddleware)
    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(sessions_router)
    return app
