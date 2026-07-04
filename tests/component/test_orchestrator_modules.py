"""Component tests — orchestrator modules together, gateway mocked."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.catalog.provider import JsonCatalogProvider
from src.checkout.service import CheckoutService
from src.gateway.ihms_models import (
    CreateHoldItemRequest,
    HoldItemResponse,
    HoldResponse,
    HoldStatus,
)
from src.session.models import SessionState
from src.session.store import InMemorySessionStore


@pytest.fixture
def catalog() -> JsonCatalogProvider:
    path = Path(__file__).resolve().parents[2] / "catalog" / "products.json"
    return JsonCatalogProvider(path)


@pytest.fixture
def checkout_service(catalog: JsonCatalogProvider) -> CheckoutService:
    ihms = MagicMock()
    ihms.create_hold = AsyncMock()
    ihms.get_hold = AsyncMock()
    ihms.release_hold = AsyncMock()
    ecops = MagicMock()
    ecops.create_order = AsyncMock()
    ecops.find_order_by_client_reference = AsyncMock(return_value=None)
    return CheckoutService.create(
        catalog=catalog,
        sessions=InMemorySessionStore(),
        ihms=ihms,
        ecops=ecops,
    )


def test_create_session_persists_with_correlation_id(checkout_service: CheckoutService) -> None:
    session = checkout_service.create_session("corr-component-1")

    assert session.correlation_id == "corr-component-1"
    assert session.state == SessionState.CREATED

    loaded = checkout_service.get_session(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id


def test_catalog_resolves_sku_for_checkout(checkout_service: CheckoutService) -> None:
    products = checkout_service.list_catalog()
    assert products

    product = checkout_service.get_product(products[0].sku)
    assert product is not None
    assert product.ihms_product_id
    assert product.ecops_item_code


@pytest.mark.asyncio
async def test_gateway_create_hold_delegates_with_observability_headers(
    checkout_service: CheckoutService,
) -> None:
    from datetime import UTC, datetime

    checkout_service.ihms.create_hold.return_value = HoldResponse(
        hold_id="hold-123",
        status=HoldStatus.ACTIVE,
        items=[HoldItemResponse(product_id="prod-widget-001", name="Widget", quantity=1)],
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )

    headers = checkout_service.observability_from_request("r1", "c1", "t1")
    items = [CreateHoldItemRequest(product_id="prod-widget-001", quantity=1)]
    result = await checkout_service.ihms_client.create_hold(items, headers)

    checkout_service.ihms.create_hold.assert_awaited_once_with(items, headers)
    assert result.hold_id == "hold-123"


def test_observability_headers_serialize(checkout_service: CheckoutService) -> None:
    headers = checkout_service.observability_from_request("r1", "c1", "t1")
    assert headers.as_dict() == {
        "X-Request-ID": "r1",
        "X-Correlation-ID": "c1",
        "X-Trace-ID": "t1",
    }
