"""Integration tests — full FastAPI app."""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from src.api import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
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


async def test_catalog_list_returns_products(client: AsyncClient) -> None:
    response = await client.get("/catalog")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 1
    assert "sku" in products[0]
    assert "ihms_product_id" in products[0]
    assert "ecops_item_code" in products[0]


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
