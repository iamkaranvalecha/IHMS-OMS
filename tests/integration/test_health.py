"""Integration tests — full FastAPI app."""

from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from src.api import create_app
from src.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ihms_base_url="http://ihms.test",
        ecops_base_url="http://ecops.test",
        ecops_bearer_token="test-token",
        catalog_source="json",
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


async def test_health_returns_observability_ids(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "request_id" in body
    assert "correlation_id" in body
    assert "trace_id" in body
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("X-Correlation-ID")
    assert response.headers.get("X-Trace-ID")


@respx.mock
async def test_catalog_list_returns_products(client: AsyncClient) -> None:
    respx.get("http://ihms.test/api/inventory").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"productId": "prod-widget-001", "availableQuantity": 100},
                {"productId": "prod-gadget-002", "availableQuantity": 50},
            ],
        )
    )
    response = await client.get("/catalog")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 1
    assert "sku" in products[0]
    assert "ihms_product_id" in products[0]
    assert "ecops_item_code" in products[0]
    assert products[0]["available_quantity"] == 100


@respx.mock
async def test_catalog_degrades_when_ihms_inventory_unavailable(client: AsyncClient) -> None:
    respx.get("http://ihms.test/api/inventory").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    response = await client.get("/catalog")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 1
    assert products[0]["available_quantity"] is None


async def test_create_and_get_session(client: AsyncClient) -> None:
    create_resp = await client.post("/sessions", json={})
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["state"] == "CREATED"
    assert created["correlation_id"]
    session_id = created["session_id"]

    get_resp = await client.get(f"/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["session_id"] == session_id


async def test_create_session_generates_unique_correlation_id(client: AsyncClient) -> None:
    first = await client.post(
        "/sessions",
        json={"correlation_id": "caller-controlled"},
        headers={"X-Correlation-ID": "caller-controlled"},
    )
    second = await client.post(
        "/sessions",
        json={"correlation_id": "caller-controlled"},
        headers={"X-Correlation-ID": "caller-controlled"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_correlation = first.json()["correlation_id"]
    second_correlation = second.json()["correlation_id"]
    assert first_correlation != "caller-controlled"
    assert second_correlation != "caller-controlled"
    assert first_correlation != second_correlation
    UUID(first_correlation)
    UUID(second_correlation)


async def test_get_session_not_found(client: AsyncClient) -> None:
    response = await client.get("/sessions/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.fixture
async def ihms_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    ihms_settings = settings.model_copy(
        update={"catalog_source": "ihms", "catalog_fallback_to_json": True}
    )
    app = create_app(ihms_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@respx.mock
async def test_catalog_falls_back_to_json_when_ihms_products_unavailable(
    ihms_client: AsyncClient,
) -> None:
    respx.get("http://ihms.test/api/products").mock(
        side_effect=httpx.ConnectError("All connection attempts failed")
    )
    respx.get("http://ihms.test/api/inventory").mock(
        side_effect=httpx.ConnectError("All connection attempts failed")
    )
    response = await ihms_client.get("/catalog")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 1
    assert products[0]["sku"] == "WIDGET-001"


@respx.mock
async def test_catalog_returns_502_when_ihms_unavailable_and_fallback_disabled() -> None:
    ihms_settings = Settings(
        ihms_base_url="http://ihms.test",
        ecops_base_url="http://ecops.test",
        ecops_bearer_token="test-token",
        catalog_source="ihms",
        catalog_fallback_to_json=False,
    )
    app = create_app(ihms_settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            respx.get("http://ihms.test/api/products").mock(
                side_effect=httpx.ConnectError("All connection attempts failed")
            )
            response = await client.get("/catalog")
    assert response.status_code == 502
    assert "Cannot reach KB-IHMS" in response.json()["detail"]
