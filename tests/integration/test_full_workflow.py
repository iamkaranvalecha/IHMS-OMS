"""Integration tests for full checkout workflows (one-click, place-order, upstream health)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from src.api import create_app
from src.settings import Settings
from tests.integration.support import (
    checkout_items,
    ecops_order_response,
    ihms_hold_response,
    mock_ecops_list_orders_empty,
    mock_fulfill,
    mock_happy_path_upstream,
    mock_inventory,
)


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


@respx.mock
async def test_place_order_on_existing_session(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]
    order_id = str(uuid4())

    mock_happy_path_upstream("hold-place-order", order_id, correlation_id)

    response = await client.post(
        f"/sessions/{session_id}/place-order",
        json=checkout_items(customer_name="Karan"),
        headers={"Idempotency-Key": "idem-place-order"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "CONFIRMED"
    assert body["order_id"] == order_id
    assert body["customer_name"] == "Karan"
    assert body["correlation_id"] == correlation_id


@respx.mock
async def test_place_order_requires_idempotency_key(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    response = await client.post(
        f"/sessions/{session_id}/place-order",
        json=checkout_items(),
    )
    assert response.status_code == 400
    assert "Idempotency-Key" in response.json()["detail"]


@respx.mock
async def test_place_order_idempotency_replay(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]
    order_id = str(uuid4())
    hold_id = "hold-idem-place"

    mock_inventory()
    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=ihms_hold_response(hold_id))
    )
    mock_ecops_list_orders_empty()
    order_route = respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=ecops_order_response(order_id, correlation_id))
    )
    respx.get(f"http://ihms.test/api/holds/{hold_id}").mock(
        return_value=httpx.Response(200, json=ihms_hold_response(hold_id))
    )
    mock_fulfill(hold_id)

    headers = {"Idempotency-Key": "idem-place-replay"}
    first = await client.post(
        f"/sessions/{session_id}/place-order",
        json=checkout_items(),
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["state"] == "CONFIRMED"

    second = await client.post(
        f"/sessions/{session_id}/place-order",
        json=checkout_items(),
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["order_id"] == order_id
    assert order_route.call_count == 1


@respx.mock
async def test_multi_item_one_click_checkout(client: AsyncClient) -> None:
    order_id = str(uuid4())
    mock_inventory()
    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=ihms_hold_response("hold-multi-checkout"))
    )
    mock_ecops_list_orders_empty()
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=ecops_order_response(order_id, "corr-multi"))
    )
    mock_fulfill("hold-multi-checkout")

    response = await client.post(
        "/sessions/checkout",
        json=checkout_items(
            items=[
                {"sku": "WIDGET-001", "quantity": 2},
                {"sku": "GADGET-002", "quantity": 1},
            ],
        ),
        headers={"Idempotency-Key": "idem-multi-checkout"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["state"] == "CONFIRMED"
    assert len(body["line_items"]) == 2


@respx.mock
async def test_one_click_checkout_compensates_on_order_failure(client: AsyncClient) -> None:
    mock_inventory()
    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=ihms_hold_response("hold-comp-checkout"))
    )
    mock_ecops_list_orders_empty()
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(500, json={"detail": "Order failed"})
    )
    release_route = respx.delete("http://ihms.test/api/holds/hold-comp-checkout").mock(
        return_value=httpx.Response(204)
    )

    response = await client.post(
        "/sessions/checkout",
        json=checkout_items(),
        headers={"Idempotency-Key": "idem-comp-checkout"},
    )
    assert response.status_code == 502
    assert release_route.call_count == 1


@respx.mock
async def test_health_upstreams_reports_connectivity(client: AsyncClient) -> None:
    respx.get("http://ihms.test/api/products").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "productId": "prod-widget-001",
                    "sku": "WIDGET-001",
                    "name": "Widget",
                    "unitPrice": 19.99,
                    "availableQuantity": 100,
                }
            ],
        )
    )
    respx.get("http://ecops.test/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    respx.get("http://ecops.test/orders").mock(return_value=httpx.Response(200, json=[]))

    response = await client.get("/health/upstreams")
    assert response.status_code == 200
    body = response.json()
    assert body["catalog_source"] == "json"
    assert body["ihms"]["ok"] is True
    assert body["ecops"]["ok"] is True
    assert body["ecops"]["token_configured"] is True
    assert body["ecops"]["auth_ok"] is True


@respx.mock
async def test_health_upstreams_auth_failure_when_token_rejected(client: AsyncClient) -> None:
    respx.get("http://ihms.test/api/products").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://ecops.test/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    respx.get("http://ecops.test/orders").mock(
        return_value=httpx.Response(401, json={"detail": "Invalid or expired credentials"})
    )

    response = await client.get("/health/upstreams")
    body = response.json()
    assert body["ecops"]["auth_ok"] is False
    assert "credentials" in str(body["ecops"].get("auth_error", ""))
