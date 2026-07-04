"""Contract tests for IHMS and EC-OPS wire formats."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
import respx
from src.gateway.ecops_client import EcOpsClient
from src.gateway.ecops_models import OrderCreate, OrderItemCreate
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient
from src.gateway.ihms_models import CreateHoldItemRequest

OBS = ObservabilityHeaders(
    request_id="req-1",
    correlation_id="corr-1",
    trace_id="trace-1",
)


@pytest.fixture
def ihms_client() -> IhmsClient:
    return IhmsClient(httpx.AsyncClient(), "http://ihms.test")


@pytest.fixture
def ecops_client() -> EcOpsClient:
    return EcOpsClient(httpx.AsyncClient(), "http://ecops.test", bearer_token="test-token")


@respx.mock
@pytest.mark.asyncio
async def test_ihms_create_hold_request_shape(ihms_client: IhmsClient) -> None:
    route = respx.post("http://ihms.test/api/holds").mock(
        return_value=httpx.Response(
            201,
            json={
                "holdId": "hold-abc",
                "status": "Active",
                "items": [{"productId": "prod-widget-001", "name": "Widget", "quantity": 2}],
                "createdAt": "2026-07-04T12:00:00+00:00",
                "expiresAt": "2026-07-04T12:15:00+00:00",
            },
        )
    )

    result = await ihms_client.create_hold(
        [CreateHoldItemRequest(product_id="prod-widget-001", quantity=2)],
        OBS,
    )

    assert route.called
    request = route.calls[0].request
    assert request.headers["X-Request-ID"] == "req-1"
    assert request.headers["X-Correlation-ID"] == "corr-1"
    assert request.headers["X-Trace-ID"] == "trace-1"
    import json

    sent = json.loads(request.content.decode())
    assert sent == {"items": [{"productId": "prod-widget-001", "quantity": 2}]}
    assert result.hold_id == "hold-abc"
    assert result.status == "Active"


@respx.mock
@pytest.mark.asyncio
async def test_ihms_release_hold_sends_delete(ihms_client: IhmsClient) -> None:
    route = respx.delete("http://ihms.test/api/holds/hold-abc").mock(
        return_value=httpx.Response(204)
    )

    await ihms_client.release_hold("hold-abc", OBS)

    assert route.called
    assert route.calls[0].request.headers["X-Correlation-ID"] == "corr-1"


@respx.mock
@pytest.mark.asyncio
async def test_ihms_get_hold_maps_409_to_conflict(ihms_client: IhmsClient) -> None:
    from src.gateway.exceptions import HoldConflictError

    respx.get("http://ihms.test/api/holds/hold-expired").mock(
        return_value=httpx.Response(409, json={"title": "Conflict", "detail": "Hold expired"})
    )

    with pytest.raises(HoldConflictError) as exc:
        await ihms_client.get_hold("hold-expired", OBS)

    assert exc.value.problem.status_code == 409


@respx.mock
@pytest.mark.asyncio
async def test_ecops_create_order_request_shape(ecops_client: EcOpsClient) -> None:
    order_id = str(uuid4())
    route = respx.post("http://ecops.test/orders").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": order_id,
                "customer_name": "Test Customer",
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
            },
        )
    )

    payload = OrderCreate(
        customer_name="Test Customer",
        items=[OrderItemCreate(product_name="WIDGET-001", quantity=1, price=Decimal("19.99"))],
    )
    result = await ecops_client.create_order(payload, OBS, idempotency_key="idem-1")

    assert route.called
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Idempotency-Key"] == "idem-1"
    assert request.headers["X-Trace-ID"] == "trace-1"
    import json

    sent = json.loads(request.content.decode())
    assert sent["customer_name"] == "Test Customer"
    assert sent["items"][0]["product_name"] == "WIDGET-001"
    assert str(result.id) == order_id


@respx.mock
@pytest.mark.asyncio
async def test_ecops_list_orders_query_param(ecops_client: EcOpsClient) -> None:
    respx.get("http://ecops.test/orders").mock(return_value=httpx.Response(200, json=[]))

    await ecops_client.list_orders(OBS, status=None)

    assert respx.calls[0].request.url.params.get("status") is None


@respx.mock
@pytest.mark.asyncio
async def test_ecops_find_order_by_client_reference(ecops_client: EcOpsClient) -> None:
    order_id = str(uuid4())
    respx.get("http://ecops.test/orders").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": order_id,
                    "customer_name": "Test",
                    "status": "PENDING",
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": None,
                    "items": [],
                    "client_reference": "corr-find",
                }
            ],
        )
    )

    result = await ecops_client.find_order_by_client_reference("corr-find", OBS)

    assert result is not None
    assert str(result.id) == order_id
    assert respx.calls[0].request.url.params.get("client_ref") == "corr-find"
