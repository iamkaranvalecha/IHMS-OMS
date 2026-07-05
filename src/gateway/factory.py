"""Gateway client factory and lifespan helpers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from src.gateway.ecops_client import EcOpsClient
from src.gateway.ihms_client import IhmsClient
from src.settings import Settings


@asynccontextmanager
async def gateway_clients(settings: Settings) -> AsyncIterator[tuple[IhmsClient, EcOpsClient]]:
    """Create shared httpx pools for IHMS and EC-OPS."""
    ihms_timeout = httpx.Timeout(
        connect=settings.ihms_connect_timeout,
        read=settings.ihms_read_timeout,
        write=settings.ihms_read_timeout,
        pool=settings.ihms_connect_timeout,
    )
    ecops_timeout = httpx.Timeout(
        connect=settings.ecops_connect_timeout,
        read=settings.ecops_read_timeout,
        write=settings.ecops_read_timeout,
        pool=settings.ecops_connect_timeout,
    )
    async with (
        httpx.AsyncClient(timeout=ihms_timeout) as ihms_http,
        httpx.AsyncClient(timeout=ecops_timeout) as ecops_http,
    ):
        ihms = IhmsClient(
            ihms_http,
            settings.ihms_base_url,
            fulfill_optional=settings.ihms_fulfill_optional,
        )
        ecops = EcOpsClient(ecops_http, settings.ecops_base_url, settings.ecops_bearer_token)
        yield ihms, ecops
