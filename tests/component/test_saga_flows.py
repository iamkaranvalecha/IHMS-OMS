"""Component tests — saga flows with gateway mocked at boundary."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.catalog.provider import JsonCatalogProvider
from src.checkout.service import CheckoutService
from src.gateway.ecops_models import OrderResponse, OrderStatus
from src.gateway.exceptions import UpstreamError, UpstreamProblem
from src.gateway.ihms_models import HoldItemResponse, HoldResponse, HoldStatus
from src.session.models import SessionState
from src.session.store import InMemorySessionStore


@pytest.fixture
def catalog() -> JsonCatalogProvider:
    path = Path(__file__).resolve().parents[2] / "catalog" / "products.json"
    return JsonCatalogProvider(path)


@pytest.fixture
def checkout(catalog: JsonCatalogProvider) -> CheckoutService:
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


@pytest.fixture
def obs(checkout: CheckoutService):
    return checkout.observability_from_request("r1", "corr-comp", "t1")


@pytest.mark.asyncio
async def test_saga_compensates_when_ecops_returns_500(
    checkout: CheckoutService, obs
) -> None:
    session = checkout.create_session("corr-comp")
    checkout.ihms.create_hold.return_value = HoldResponse(
        hold_id="hold-comp",
        status=HoldStatus.ACTIVE,
        items=[HoldItemResponse(product_id="prod-widget-001", name="Widget", quantity=1)],
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    held = await checkout.place_hold(
        session.session_id, "WIDGET-001", 1, "Customer", obs
    )
    assert held.state == SessionState.HELD

    checkout.ecops.create_order.side_effect = UpstreamError(
        UpstreamProblem(status_code=500, detail="Internal error")
    )

    with pytest.raises(UpstreamError):
        await checkout.confirm(held.session_id, None, "idem-comp-1", obs)

    updated = checkout.get_session(held.session_id)
    assert updated is not None
    assert updated.state == SessionState.COMPENSATED
    checkout.ihms.release_hold.assert_awaited()


@pytest.mark.asyncio
async def test_saga_happy_path_hold_then_confirm(checkout: CheckoutService, obs) -> None:
    session = checkout.create_session("corr-happy")
    checkout.ihms.create_hold.return_value = HoldResponse(
        hold_id="hold-happy",
        status=HoldStatus.ACTIVE,
        items=[HoldItemResponse(product_id="prod-widget-001", name="Widget", quantity=1)],
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    held = await checkout.place_hold(
        session.session_id, "WIDGET-001", 1, "Happy Customer", obs
    )
    order_id = uuid4()
    checkout.ecops.create_order.return_value = OrderResponse(
        id=order_id,
        customer_name="Happy Customer",
        status=OrderStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=None,
        items=[],
    )

    result = await checkout.confirm(held.session_id, None, "idem-happy", obs)

    assert result.session.state == SessionState.CONFIRMED
    assert result.session.order_id == str(order_id)
    sent_payload = checkout.ecops.create_order.await_args.args[0]
    assert sent_payload.client_reference == "corr-happy"
    assert sent_payload.items[0].product_name == "WIDGET-001"
    assert sent_payload.items[0].price == Decimal("19.99")


@pytest.mark.asyncio
async def test_saga_abandon_before_hold(checkout: CheckoutService, obs) -> None:
    session = checkout.create_session("corr-abandon")
    abandoned = await checkout.abandon(session.session_id, obs)
    assert abandoned.state == SessionState.ABANDONED
    checkout.ihms.release_hold.assert_not_awaited()
