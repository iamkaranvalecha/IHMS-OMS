"""End-to-end tests — require compose.full.yml stack (STACK=1)."""

from __future__ import annotations

import httpx
import pytest
from tests.e2e.conftest import ECOPS_ADMIN_URL, IHMS_ADMIN_URL


@pytest.mark.e2e
async def test_metrics_endpoint(api: httpx.AsyncClient) -> None:
    response = await api.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    assert "holds_placed_total" in response.text
    assert "# TYPE confirms_success_total counter" in response.text


@pytest.mark.e2e
async def test_health(api: httpx.AsyncClient) -> None:
    response = await api.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["request_id"]
    assert body["correlation_id"]


@pytest.mark.e2e
async def test_catalog_lists_products(api: httpx.AsyncClient) -> None:
    response = await api.get("/catalog")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 1
    assert products[0]["sku"] == "WIDGET-001"


@pytest.mark.e2e
async def test_happy_path_hold_and_confirm(api: httpx.AsyncClient) -> None:
    create = await api.post("/sessions", json={})
    assert create.status_code == 201
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    hold = await api.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "E2E Customer"},
    )
    assert hold.status_code == 200
    held = hold.json()
    assert held["state"] == "HELD"
    assert held["hold_id"]
    assert held["expires_at"]

    confirm = await api.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": f"e2e-happy-{correlation_id}"},
    )
    assert confirm.status_code == 200
    confirmed = confirm.json()
    assert confirmed["state"] == "CONFIRMED"
    assert confirmed["order_id"]

    get_resp = await api.get(f"/sessions/{session_id}")
    assert get_resp.json()["state"] == "CONFIRMED"


@pytest.mark.e2e
async def test_hold_fails_with_409(
    api: httpx.AsyncClient,
    upstream_admin: httpx.AsyncClient,
) -> None:
    await upstream_admin.post(f"{IHMS_ADMIN_URL}/_test/scenario", json={"force_hold_status": 409})

    create = await api.post("/sessions", json={})
    session_id = create.json()["session_id"]

    hold = await api.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "E2E Customer"},
    )
    assert hold.status_code == 409

    get_resp = await api.get(f"/sessions/{session_id}")
    assert get_resp.json()["state"] == "CREATED"


@pytest.mark.e2e
async def test_confirm_compensates_when_order_fails(
    api: httpx.AsyncClient,
    upstream_admin: httpx.AsyncClient,
) -> None:
    await upstream_admin.post(f"{ECOPS_ADMIN_URL}/_test/scenario", json={"scenario": "order-error"})

    create = await api.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    hold = await api.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "E2E Customer"},
    )
    assert hold.status_code == 200
    assert hold.json()["state"] == "HELD"

    confirm = await api.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": f"e2e-compensate-{correlation_id}"},
    )
    assert confirm.status_code == 502

    get_resp = await api.get(f"/sessions/{session_id}")
    assert get_resp.json()["state"] == "COMPENSATED"


@pytest.mark.e2e
async def test_reconcile_after_order_timeout(
    api: httpx.AsyncClient,
    upstream_admin: httpx.AsyncClient,
) -> None:
    await upstream_admin.post(
        f"{ECOPS_ADMIN_URL}/_test/scenario",
        json={"scenario": "order-timeout"},
    )

    create = await api.post("/sessions", json={})
    session_id = create.json()["session_id"]
    correlation_id = create.json()["correlation_id"]

    hold = await api.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "E2E Customer"},
    )
    assert hold.status_code == 200

    confirm = await api.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": f"e2e-reconcile-{correlation_id}"},
        timeout=15.0,
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["state"] == "RECONCILED"
    assert body["order_id"]


@pytest.mark.e2e
async def test_abandon_releases_hold(api: httpx.AsyncClient) -> None:
    create = await api.post("/sessions", json={})
    session_id = create.json()["session_id"]

    hold = await api.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "E2E Customer"},
    )
    assert hold.status_code == 200

    abandon = await api.delete(f"/sessions/{session_id}")
    assert abandon.status_code == 200
    assert abandon.json()["state"] == "ABANDONED"
