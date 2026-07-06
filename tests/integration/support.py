"""Shared respx helpers for integration workflow tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import respx


def ihms_hold_response(hold_id: str = "hold-int") -> dict:
    now = datetime.now(UTC)
    return {
        "holdId": hold_id,
        "status": "Active",
        "items": [{"productId": "prod-widget-001", "name": "Widget", "quantity": 1}],
        "createdAt": now.isoformat(),
        "expiresAt": (now + timedelta(minutes=10)).isoformat(),
    }


def ecops_order_response(order_id: str, client_ref: str) -> dict:
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


def mock_fulfill(hold_id: str) -> None:
    respx.post(f"http://ihms.test/api/holds/{hold_id}/fulfill").mock(
        return_value=httpx.Response(204)
    )


def mock_ecops_list_orders_empty() -> None:
    respx.get("http://ecops.test/orders").mock(return_value=httpx.Response(200, json=[]))


def mock_inventory(widget_available: int = 100, gadget_available: int = 100) -> None:
    respx.get("http://ihms.test/api/inventory").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"productId": "prod-widget-001", "availableQuantity": widget_available},
                {"productId": "prod-gadget-002", "availableQuantity": gadget_available},
            ],
        )
    )


def mock_happy_path_upstream(hold_id: str, order_id: str, correlation_id: str) -> None:
    """Wire mocks for hold → order → fulfill."""
    mock_inventory()
    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=ihms_hold_response(hold_id))
    )
    mock_ecops_list_orders_empty()
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(201, json=ecops_order_response(order_id, correlation_id))
    )
    respx.get(f"http://ihms.test/api/holds/{hold_id}").mock(
        return_value=httpx.Response(200, json=ihms_hold_response(hold_id))
    )
    mock_fulfill(hold_id)


def checkout_items(
    *,
    customer_name: str = "Workflow Customer",
    items: list[dict[str, object]] | None = None,
) -> dict:
    if items is None:
        items = [{"sku": "WIDGET-001", "quantity": 1}]
    body: dict[str, object] = {"items": items}
    if customer_name:
        body["customer_name"] = customer_name
    return body
