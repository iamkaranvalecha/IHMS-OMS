"""Wire-compatible EC-OPS mock for full-stack E2E."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ORDER_TIMEOUT_SLEEP_SECONDS = 30


class OrderItemIn(BaseModel):
    product_name: str
    quantity: int = Field(gt=0)
    price: Decimal = Field(ge=Decimal("0"))


class OrderCreateBody(BaseModel):
    customer_name: str = Field(min_length=1)
    items: list[OrderItemIn] = Field(min_length=1)


@dataclass
class MockState:
    orders: list[dict[str, Any]] = field(default_factory=list)
    scenario: str | None = None


state = MockState()
app = FastAPI(title="mock-ecops", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/orders")
async def list_orders() -> list[dict[str, Any]]:
    return state.orders


@app.get("/orders/{order_id}")
async def get_order(order_id: str) -> JSONResponse:
    for order in state.orders:
        if order["id"] == order_id:
            return JSONResponse(content=order)
    return JSONResponse(status_code=404, content={"detail": "Order not found"})


@app.post("/orders", status_code=201)
async def create_order(body: OrderCreateBody, request: Request) -> JSONResponse:
    correlation_id = request.headers.get("X-Correlation-ID")
    scenario = request.headers.get("X-Test-Scenario") or state.scenario

    if scenario == "order-error":
        return JSONResponse(status_code=500, content={"detail": "Order failed"})

    order = _build_order(body, correlation_id)

    if scenario == "order-timeout":
        state.orders.append(order)
        await asyncio.sleep(ORDER_TIMEOUT_SLEEP_SECONDS)
        return JSONResponse(status_code=201, content=order)

    state.orders.append(order)
    return JSONResponse(status_code=201, content=order)


@app.post("/_test/reset")
async def reset_state() -> dict[str, str]:
    state.orders.clear()
    state.scenario = None
    return {"status": "reset"}


class ScenarioBody(BaseModel):
    scenario: str | None = None


@app.post("/_test/scenario")
async def set_scenario(body: ScenarioBody) -> dict[str, str]:
    state.scenario = body.scenario
    return {"status": "ok", "scenario": body.scenario or ""}


def _build_order(body: OrderCreateBody, client_reference: str | None) -> dict[str, Any]:
    order_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    items = []
    for item in body.items:
        items.append(
            {
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "price": str(item.price),
            }
        )
    order: dict[str, Any] = {
        "id": order_id,
        "customer_name": body.customer_name,
        "status": "PENDING",
        "created_at": now,
        "updated_at": None,
        "items": items,
    }
    if client_reference:
        order["client_reference"] = client_reference
    return order
