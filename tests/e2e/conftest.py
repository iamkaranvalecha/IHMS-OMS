"""Fixtures for full-stack E2E tests against docker compose."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
import pytest

ORCHESTRATOR_URL = os.environ.get(
    "E2E_ORCHESTRATOR_URL",
    f"http://localhost:{os.environ.get('ORCHESTRATOR_PORT', '8000')}",
)
IHMS_ADMIN_URL = os.environ.get(
    "E2E_IHMS_ADMIN_URL",
    f"http://localhost:{os.environ.get('IHMS_PORT', '8080')}",
)
ECOPS_ADMIN_URL = os.environ.get(
    "E2E_ECOPS_ADMIN_URL",
    f"http://localhost:{os.environ.get('ECOPS_PORT', '8012')}",
)


@pytest.fixture(autouse=True)
async def reset_mock_upstreams() -> AsyncIterator[None]:
    """Isolate scenarios by resetting in-memory mock state."""
    async with httpx.AsyncClient(timeout=10.0) as admin:
        await admin.post(f"{IHMS_ADMIN_URL}/_test/reset")
        await admin.post(f"{ECOPS_ADMIN_URL}/_test/reset")
    yield
    async with httpx.AsyncClient(timeout=10.0) as admin:
        await admin.post(f"{IHMS_ADMIN_URL}/_test/reset")
        await admin.post(f"{ECOPS_ADMIN_URL}/_test/reset")


@pytest.fixture
async def api() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=ORCHESTRATOR_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
async def upstream_admin() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client
