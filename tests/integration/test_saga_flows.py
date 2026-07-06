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
        catalog_source="json",
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


def _mock_fulfill(hold_id: str) -> None:
    respx.post(f"http://ihms.test/api/holds/{hold_id}/fulfill").mock(
        return_value=httpx.Response(204)
    )


def _mock_ecops_list_orders_empty() -> None:
    respx.get("http://ecops.test/orders").mock(return_value=httpx.Response(200, json=[]))


def _mock_inventory(widget_available: int = 100, gadget_available: int = 100) -> None:
    respx.get("http://ihms.test/api/inventory").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"productId": "prod-widget-001", "availableQuantity": widget_available},
                {"productId": "prod-gadget-002", "availableQuantity": gadget_available},
            ],
        )
    )


def _hold_body(
    customer_name: str = "Customer",
    *,
    items: list[dict[str, object]] | None = None,
) -> dict:
    if items is None:
        items = [{"sku": "WIDGET-001", "quantity": 1}]
    return {"items": items, "customer_name": customer_name}


@respx.mock
async def test_happy_path_hold_and_confirm(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    assert create.status_code == 201
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response())
    )
    _mock_inventory()
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body("Integration Customer"),
    )
    assert hold_resp.status_code == 200, hold_resp.text
    assert hold_resp.json()["state"] == "HELD"
    assert hold_resp.json()["hold_id"] == "hold-int"

    order_id = str(uuid4())
    _mock_ecops_list_orders_empty()
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=_ecops_order_response(order_id, correlation_id))
    )
    respx.get("http://ihms.test/api/holds/hold-int").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response())
    )
    _mock_fulfill("hold-int")

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
    _mock_inventory()
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
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
    _mock_inventory()
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )
    assert hold_resp.status_code == 200, hold_resp.text
    assert hold_resp.json()["state"] == "HELD"

    respx.get("http://ihms.test/api/holds/hold-fail").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-fail"))
    )
    _mock_ecops_list_orders_empty()
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
    _mock_inventory()
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )
    assert hold_resp.status_code == 200
    assert hold_resp.json()["state"] == "HELD"

    order_id = str(uuid4())
    _mock_ecops_list_orders_empty()
    order_route = respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=_ecops_order_response(order_id, correlation_id))
    )
    respx.get("http://ihms.test/api/holds/hold-dup").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-dup"))
    )
    _mock_fulfill("hold-dup")

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
    _mock_inventory()
    await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
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
    _mock_inventory()
    await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )

    order_id = str(uuid4())
    _mock_ecops_list_orders_empty()
    order_route = respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(
            201,
            json=_ecops_order_response(order_id, session_correlation_id),
        )
    )
    respx.get("http://ihms.test/api/holds/hold-corr").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-corr"))
    )
    _mock_fulfill("hold-corr")

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
    _mock_inventory()
    await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )

    order_id = str(uuid4())
    respx.post("http://ecops.test/orders").mock(side_effect=httpx.TimeoutException("timeout"))
    respx.get("http://ihms.test/api/holds/hold-reconcile").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-reconcile"))
    )
    respx.get("http://ecops.test/orders").mock(
        side_effect=[
            httpx.Response(200, json=[]),
            httpx.Response(
                200,
                json=[_ecops_order_response(order_id, correlation_id)],
            ),
        ]
    )
    _mock_fulfill("hold-reconcile")

    confirm = await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "idem-reconcile"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["state"] == "RECONCILED"
    assert confirm.json()["order_id"] == order_id


@respx.mock
async def test_reconcile_lookup_failure_retains_hold(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-reconcile-error"))
    )
    _mock_inventory()
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )
    assert hold_resp.status_code == 200, hold_resp.text
    assert hold_resp.json()["state"] == "HELD"

    respx.post("http://ecops.test/orders").mock(side_effect=httpx.TimeoutException("timeout"))
    respx.get("http://ihms.test/api/holds/hold-reconcile-error").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-reconcile-error"))
    )
    respx.get("http://ecops.test/orders").mock(
        side_effect=[
            httpx.Response(200, json=[]),
            httpx.Response(503, json={"detail": "Order list unavailable"}),
        ]
    )
    confirm = await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "idem-reconcile-error"},
    )

    assert confirm.status_code == 503, confirm.json()
    get_resp = await client.get(f"/sessions/{session_id}")
    body = get_resp.json()
    assert body["state"] == "HELD"
    assert body["order_id"] is None


@respx.mock
async def test_retry_after_reconcile_lookup_failure_resolves_without_duplicate_order(
    client: AsyncClient,
) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-unknown"))
    )
    _mock_inventory()
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )
    assert hold_resp.status_code == 200, hold_resp.text

    order_id = str(uuid4())
    order_route = respx.post("http://ecops.test/orders").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    hold_check = respx.get("http://ihms.test/api/holds/hold-unknown").mock(
        side_effect=[
            httpx.Response(200, json=_ihms_hold_response("hold-unknown")),
            httpx.Response(409, json={"title": "Conflict", "detail": "Hold expired"}),
        ]
    )
    list_route = respx.get("http://ecops.test/orders").mock(
        side_effect=[
            httpx.Response(200, json=[]),
            httpx.Response(503, json={"detail": "Order list unavailable"}),
            httpx.Response(200, json=[_ecops_order_response(order_id, correlation_id)]),
        ]
    )
    _mock_fulfill("hold-unknown")

    headers = {"Idempotency-Key": "idem-unknown"}
    first = await client.post(f"/sessions/{session_id}/confirm", json={}, headers=headers)
    assert first.status_code == 503, first.json()

    second = await client.post(f"/sessions/{session_id}/confirm", json={}, headers=headers)
    assert second.status_code == 200, second.json()
    assert second.json()["state"] == "RECONCILED"
    assert second.json()["order_id"] == order_id
    assert order_route.call_count == 1
    assert hold_check.call_count == 1
    assert list_route.call_count == 3


@respx.mock
async def test_timeout_does_not_reconcile_unmatched_order(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-unmatched"))
    )
    _mock_inventory()
    await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )

    order_route = respx.post("http://ecops.test/orders").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    respx.get("http://ihms.test/api/holds/hold-unmatched").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-unmatched"))
    )
    respx.get("http://ecops.test/orders").mock(
        side_effect=[
            httpx.Response(200, json=[]),
            httpx.Response(200, json=[]),
            httpx.Response(200, json=[]),
            httpx.Response(200, json=[]),
        ]
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


@respx.mock
async def test_hold_rejected_when_inventory_insufficient(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    _mock_inventory(widget_available=0)
    hold_route = respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-never"))
    )
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )

    assert hold_resp.status_code == 409
    assert not hold_route.called
    get_resp = await client.get(f"/sessions/{session_id}")
    assert get_resp.json()["state"] == "CREATED"


@respx.mock
async def test_confirm_fulfill_pending_then_retry(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-pending"))
    )
    _mock_inventory()
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(),
    )
    assert hold_resp.status_code == 200, hold_resp.text

    order_id = str(uuid4())
    _mock_ecops_list_orders_empty()
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=_ecops_order_response(order_id, correlation_id))
    )
    respx.get("http://ihms.test/api/holds/hold-pending").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-pending"))
    )
    fulfill_route = respx.post("http://ihms.test/api/holds/hold-pending/fulfill").mock(
        side_effect=[
            httpx.TimeoutException("timeout"),
            httpx.TimeoutException("timeout"),
            httpx.TimeoutException("timeout"),
            httpx.Response(204),
        ]
    )

    headers = {"Idempotency-Key": "idem-fulfill-pending"}
    first = await client.post(f"/sessions/{session_id}/confirm", json={}, headers=headers)
    assert first.status_code == 200, first.json()
    assert first.json()["state"] == "FULFILL_PENDING"
    assert first.json()["order_id"] == order_id

    second = await client.post(f"/sessions/{session_id}/confirm", json={}, headers=headers)
    assert second.status_code == 200, second.json()
    assert second.json()["state"] == "CONFIRMED"
    assert fulfill_route.call_count >= 2


@respx.mock
async def test_multi_item_hold_and_confirm(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-multi"))
    )
    _mock_inventory()
    hold_resp = await client.post(
        f"/sessions/{session_id}/hold",
        json=_hold_body(
            "Multi Customer",
            items=[
                {"sku": "WIDGET-001", "quantity": 2},
                {"sku": "GADGET-002", "quantity": 1},
            ],
        ),
    )
    assert hold_resp.status_code == 200, hold_resp.text
    body = hold_resp.json()
    assert body["state"] == "HELD"
    assert len(body["line_items"]) == 2

    order_id = str(uuid4())
    _mock_ecops_list_orders_empty()
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=_ecops_order_response(order_id, correlation_id))
    )
    respx.get("http://ihms.test/api/holds/hold-multi").mock(
        return_value=httpx.Response(200, json=_ihms_hold_response("hold-multi"))
    )
    _mock_fulfill("hold-multi")

    confirm = await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "idem-multi"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["state"] == "CONFIRMED"
    assert confirm.json()["order_id"] == order_id


@respx.mock
async def test_one_click_checkout(client: AsyncClient) -> None:
    _mock_inventory()
    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold_response("hold-checkout"))
    )
    order_id = str(uuid4())
    _mock_ecops_list_orders_empty()
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(
            201,
            json=_ecops_order_response(order_id, "unused-will-be-session-correlation"),
        )
    )
    _mock_fulfill("hold-checkout")

    response = await client.post(
        "/sessions/checkout",
        json={"items": [{"sku": "WIDGET-001", "quantity": 1}]},
        headers={"Idempotency-Key": "idem-one-click"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["state"] == "CONFIRMED"
    assert body["order_id"] == order_id
    assert body["correlation_id"]
    assert response.headers.get("X-Trace-ID")
    assert response.headers.get("X-Correlation-ID")
