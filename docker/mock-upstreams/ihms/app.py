"""Wire-compatible KB-IHMS mock for full-stack E2E."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

PRODUCT_NAMES = {
    "prod-widget-001": "Standard Widget",
    "prod-gadget-002": "Premium Gadget",
}

PRODUCT_CATALOG = [
    {
        "productId": "prod-widget-001",
        "sku": "WIDGET-001",
        "name": "Standard Widget",
        "description": "Reliable everyday widget",
        "category": "Widgets",
        "unitPrice": 19.99,
        "currency": "USD",
        "availableQuantity": 100,
        "imageUrl": "",
        "sellable": True,
    },
    {
        "productId": "prod-gadget-002",
        "sku": "GADGET-002",
        "name": "Premium Gadget",
        "description": "Feature-rich premium gadget",
        "category": "Gadgets",
        "unitPrice": 49.99,
        "currency": "USD",
        "availableQuantity": 50,
        "imageUrl": "",
        "sellable": True,
    },
]

DEFAULT_INVENTORY = {
    "prod-widget-001": 100,
    "prod-gadget-002": 50,
}


class HoldItemIn(BaseModel):
    product_id: str = Field(alias="productId")
    quantity: int

    model_config = {"populate_by_name": True}


class CreateHoldBody(BaseModel):
    items: list[HoldItemIn]


@dataclass
class HoldRecord:
    hold_id: str
    status: str
    items: list[dict[str, Any]]
    created_at: datetime
    expires_at: datetime
    reserved: dict[str, int] = field(default_factory=dict)


@dataclass
class MockState:
    inventory: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_INVENTORY))
    holds: dict[str, HoldRecord] = field(default_factory=dict)
    force_hold_status: int | None = None


state = MockState()
app = FastAPI(title="mock-ihms", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/products")
async def list_products() -> list[dict[str, Any]]:
    return [
        {
            **product,
            "availableQuantity": state.inventory.get(product["productId"], 0),
        }
        for product in PRODUCT_CATALOG
        if product.get("sellable", True)
    ]


@app.get("/api/inventory")
async def list_inventory() -> list[dict[str, Any]]:
    return [
        {"productId": product_id, "availableQuantity": qty}
        for product_id, qty in state.inventory.items()
    ]


@app.post("/api/holds", status_code=201)
async def create_hold(body: CreateHoldBody) -> JSONResponse:
    if state.force_hold_status == 409:
        return JSONResponse(
            status_code=409,
            content={"title": "Conflict", "detail": "Insufficient stock"},
        )

    reserved: dict[str, int] = {}
    response_items: list[dict[str, Any]] = []
    for item in body.items:
        available = state.inventory.get(item.product_id, 0)
        if item.quantity > available:
            return JSONResponse(
                status_code=409,
                content={"title": "Conflict", "detail": "Insufficient stock"},
            )
        reserved[item.product_id] = item.quantity
        response_items.append(
            {
                "productId": item.product_id,
                "name": PRODUCT_NAMES.get(item.product_id, item.product_id),
                "quantity": item.quantity,
            }
        )

    for product_id, qty in reserved.items():
        state.inventory[product_id] -= qty

    now = datetime.now(UTC)
    hold_id = f"hold-{uuid.uuid4().hex[:12]}"
    record = HoldRecord(
        hold_id=hold_id,
        status="Active",
        items=response_items,
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        reserved=reserved,
    )
    state.holds[hold_id] = record
    return JSONResponse(status_code=201, content=_hold_payload(record))


@app.get("/api/holds/{hold_id}")
async def get_hold(hold_id: str) -> JSONResponse:
    record = state.holds.get(hold_id)
    if record is None:
        return JSONResponse(status_code=404, content={"title": "Not Found", "detail": "Hold missing"})
    if record.status == "Released":
        return JSONResponse(
            status_code=409,
            content={"title": "Conflict", "detail": "Hold expired"},
        )
    return JSONResponse(content=_hold_payload(record))


@app.delete("/api/holds/{hold_id}")
async def release_hold(hold_id: str) -> Response:
    record = state.holds.get(hold_id)
    if record is None:
        return Response(status_code=404)
    if record.status == "Fulfilled":
        return Response(status_code=409)
    state.holds.pop(hold_id, None)
    if record.status != "Fulfilled":
        for product_id, qty in record.reserved.items():
            state.inventory[product_id] = state.inventory.get(product_id, 0) + qty
    return Response(status_code=204)


@app.post("/api/holds/{hold_id}/fulfill")
async def fulfill_hold(hold_id: str) -> JSONResponse:
    record = state.holds.get(hold_id)
    if record is None:
        return JSONResponse(status_code=404, content={"title": "Not Found", "detail": "Hold missing"})
    if record.status == "Fulfilled":
        return JSONResponse(content=_hold_payload(record))
    record.status = "Fulfilled"
    return JSONResponse(content=_hold_payload(record))


@app.post("/_test/reset")
async def reset_state() -> dict[str, str]:
    state.inventory = dict(DEFAULT_INVENTORY)
    state.holds.clear()
    state.force_hold_status = None
    return {"status": "reset"}


class ScenarioBody(BaseModel):
    force_hold_status: int | None = None


@app.post("/_test/scenario")
async def set_scenario(body: ScenarioBody) -> dict[str, str]:
    state.force_hold_status = body.force_hold_status
    return {"status": "ok"}


def _hold_payload(record: HoldRecord) -> dict[str, Any]:
    return {
        "holdId": record.hold_id,
        "status": record.status,
        "items": record.items,
        "createdAt": record.created_at.isoformat(),
        "expiresAt": record.expires_at.isoformat(),
    }
