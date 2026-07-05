"""Integration tests for saga HTTP flows — upstreams mocked via respx."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


def _ihms_hold_response(hold_id: str = "hold-int") -> dict:
    now = datetime.now(UTC)
    return {
        "holdId": hold_id,
        "status": "Active",
        "items": [{"productId": "prod-widget-001", "name": "Widget", "quantity": 1}],
        "createdAt": now.isoformat(),
        "expiresAt": (now + timedelta(minutes=10)).isoformat(),
    }


def _ecops_order_response(order_id: str, client_ref: str) -> dict:
    return {
        "id": order_id,
        "customer_name": "Integration Customer",
        "status": "PENDING",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": None,
        "items": [
            {
                "id": str(uuid4()),
                "order_id": order_id,
                "product_name": "WIDGET-001",
                "quantity": 1,
                "price": "19.99",
            }
        ],
        "client_reference": client_ref,
    }


@respx.mock
async def test_happy_path_hold_and_confirm(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    assert create.status_code == 201
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response())
    )
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Integration Customer"},
    )
    assert hold_resp.status_code == 200
    assert hold_resp.json()["state"] == "HELD"
    assert hold_resp.json()["hold_id"] == "hold-int"

    order_id = str(uuid4())
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=_ecops_order_response(order_id, correlation_id))
    )
    respx.get("http://ihms.test/api/holds/hold-int").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response())
    )

    confirm = await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "idem-int-1"},
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["state"] == "CONFIRMED"
    assert body["order_id"] == order_id


@respx.mock
async def test_hold_fails_with_409(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(409, json={"title": "Conflict", "detail": "Insufficient stock"})
    )
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Customer"},
    )
    assert hold_resp.status_code == 409

    get_resp = await client.get(f"/sessions/{session_id}")
    assert get_resp.json()["state"] == "CREATED"


@respx.mock
async def test_confirm_compensates_when_order_fails(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-fail"))
    )
    await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Customer"},
    )

    respx.get("http://ihms.test/api/holds/hold-fail").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-fail"))
    )
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(500, json={"detail": "Order failed"})
    )
    release = respx.delete("http://ihms.test/api/holds/hold-fail").mock(
        return_value=httpx.Response(204)
    )

    confirm = await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "idem-fail"},
    )
    assert confirm.status_code == 502
    assert release.called

    get_resp = await client.get(f"/sessions/{session_id}")
    assert get_resp.json()["state"] == "COMPENSATED"


@respx.mock
async def test_duplicate_confirm_returns_cached(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-dup"))
    )
    await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Customer"},
    )

    order_id = str(uuid4())
    order_route = respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=_ecops_order_response(order_id, correlation_id))
    )
    respx.get("http://ihms.test/api/holds/hold-dup").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-dup"))
    )

    headers = {"Idempotency-Key": "idem-dup-key"}
    first = await client.post(f"/sessions/{session_id}/confirm", json={}, headers=headers)
    second = await client.post(f"/sessions/{session_id}/confirm", json={}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["order_id"] == order_id
    assert second.json()["order_id"] == order_id
    assert order_route.call_count == 1


@respx.mock
async def test_abandon_releases_hold(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-cancel"))
    )
    await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Customer"},
    )
    release = respx.delete("http://ihms.test/api/holds/hold-cancel").mock(
        return_value=httpx.Response(204)
    )

    abandon = await client.delete(f"/sessions/{session_id}")
    assert abandon.status_code == 200
    assert abandon.json()["state"] == "ABANDONED"
    assert release.called


@respx.mock
async def test_confirm_requires_idempotency_key(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    resp = await client.post(f"/sessions/{session_id}/confirm", json={})
    assert resp.status_code == 400


@respx.mock
async def test_confirm_sends_session_correlation_to_ecops(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    session_correlation_id = create.json()["correlation_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-corr"))
    )
    await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Customer"},
    )

    order_id = str(uuid4())
    order_route = respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(
            201,
            json=_ecops_order_response(order_id, session_correlation_id),
        )
    )
    respx.get("http://ihms.test/api/holds/hold-corr").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-corr"))
    )

    confirm = await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "idem-corr"},
    )
    assert confirm.status_code == 200
    assert order_route.called
    assert order_route.calls[0].request.headers["X-Correlation-ID"] == session_correlation_id


@respx.mock
async def test_reconcile_after_order_timeout(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-reconcile"))
    )
    await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Customer"},
    )

    order_id = str(uuid4())
    respx.post("http://ecops.test/orders").mock(side_effect=httpx.TimeoutException("timeout"))
    respx.get("http://ihms.test/api/holds/hold-reconcile").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-reconcile"))
    )
    respx.get("http://ecops.test/orders").mock(
        return_value=httpx.Response(
            200,
            json=[_ecops_order_response(order_id, correlation_id)],
        )
    )

    confirm = await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "idem-reconcile"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["state"] == "RECONCILED"
    assert confirm.json()["order_id"] == order_id


@respx.mock
async def test_timeout_does_not_reconcile_unmatched_order(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-unmatched"))
    )
    await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Customer"},
    )

    unrelated_order = str(uuid4())
    order_route = respx.post("http://ecops.test/orders").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    respx.get("http://ihms.test/api/holds/hold-unmatched").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-unmatched"))
    )
    respx.get("http://ecops.test/orders").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": unrelated_order,
                    "customer_name": "Someone Else",
                    "status": "PENDING",
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": None,
                    "items": [],
                }
            ],
        )
    )
    release = respx.delete("http://ihms.test/api/holds/hold-unmatched").mock(
        return_value=httpx.Response(204)
    )

    confirm = await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "idem-unmatched"},
    )

    assert confirm.status_code == 503
    assert order_route.call_count == 1
    assert release.called
    get_resp = await client.get(f"/sessions/{session_id}")
    body = get_resp.json()
    assert body["state"] == "COMPENSATED"
    assert body["order_id"] is None
