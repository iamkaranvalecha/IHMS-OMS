"""Integration tests for observability — logs and metrics."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

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


def _ihms_hold(hold_id: str = "hold-obs") -> dict:
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    return {
        "holdId": hold_id,
        "status": "Active",
        "items": [{"productId": "prod-widget-001", "name": "Widget", "quantity": 1}],
        "createdAt": now.isoformat(),
        "expiresAt": (now + timedelta(minutes=10)).isoformat(),
    }


@respx.mock
async def test_metrics_increment_on_happy_path(client: AsyncClient) -> None:
    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold())
    )
    await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Obs Customer"},
    )

    from uuid import uuid4

    order_id = str(uuid4())
    correlation_id = create.json()["correlation_id"]
    respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": order_id,
                "customer_name": "Obs Customer",
                "status": "PENDING",
                "created_at": "2026-07-05T12:00:00+00:00",
                "updated_at": None,
                "items": [],
                "client_reference": correlation_id,
            },
        )
    )
    respx.get("http://ihms.test/api/holds/hold-obs").mock(
        return_value=httpx.Response(200, json=_ihms_hold())
    )
    await client.post(
        f"/sessions/{session_id}/confirm",
        json={},
        headers={"Idempotency-Key": "obs-metrics-1"},
    )

    metrics = await client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.text
    assert "holds_placed_total 1" in body
    assert "confirms_success_total 1" in body


@respx.mock
async def test_saga_emits_structured_log_steps(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="checkout.saga")

    create = await client.post("/sessions", json={})
    session_id = create.json()["session_id"]

    respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(201, json=_ihms_hold("hold-log"))
    )
    await client.post(
        f"/sessions/{session_id}/hold",
        json={"sku": "WIDGET-001", "quantity": 1, "customer_name": "Log Customer"},
    )

    steps = [getattr(record, "step", None) for record in caplog.records]
    assert "place_hold" in steps


@respx.mock
async def test_http_middleware_logs_request(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="checkout.http")
    await client.get("/health")
    assert any(getattr(r, "step", None) == "http_request" for r in caplog.records)


async def test_metrics_endpoint_content_type(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "# TYPE holds_placed_total counter" in response.text
