"""Unit tests for saga coordinator logic."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.catalog.provider import JsonCatalogProvider
from src.gateway.ecops_models import OrderResponse, OrderStatus
from src.gateway.exceptions import (
    GatewayError,
    GatewayTimeoutError,
    HoldConflictError,
    UpstreamError,
    UpstreamProblem,
)
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_models import HoldItemResponse, HoldResponse, HoldStatus
from src.saga.coordinator import SagaCoordinator
from src.saga.exceptions import (
    CompensationIncompleteError,
    HoldExpiredError,
    InvalidStateTransitionError,
    SessionNotFoundError,
)
from src.saga.idempotency import InMemoryIdempotencyStore
from src.session.models import CheckoutSession, SessionLineItem, SessionState
from src.session.store import InMemorySessionStore, LockedSessionStore


@pytest.fixture
def catalog() -> JsonCatalogProvider:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "catalog" / "products.json"
    return JsonCatalogProvider(path)


@pytest.fixture
def obs() -> ObservabilityHeaders:
    return ObservabilityHeaders(request_id="r1", correlation_id="corr-unit", trace_id="t1")


@pytest.fixture
def saga(catalog: JsonCatalogProvider) -> SagaCoordinator:
    ihms = MagicMock()
    ihms.create_hold = AsyncMock()
    ihms.get_hold = AsyncMock()
    ihms.release_hold = AsyncMock()
    ihms.fulfill_hold = AsyncMock()
    ecops = MagicMock()
    ecops.create_order = AsyncMock()
    ecops.find_order_by_client_reference = AsyncMock(return_value=None)
    return SagaCoordinator(
        catalog=catalog,
        sessions=LockedSessionStore(InMemorySessionStore()),
        ihms=ihms,
        ecops=ecops,
        idempotency=InMemoryIdempotencyStore(),
    )


def _held_session(correlation_id: str = "corr-unit") -> CheckoutSession:
    return CheckoutSession(
        correlation_id=correlation_id,
        state=SessionState.HELD,
        hold_id="hold-1",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        customer_name="Test Customer",
        line_items=[
            SessionLineItem(
                sku="WIDGET-001",
                name="Standard Widget",
                ihms_product_id="prod-widget-001",
                ecops_item_code="WIDGET-001",
                quantity=1,
                unit_price=19.99,
            )
        ],
    )


@pytest.mark.asyncio
async def test_place_hold_transitions_to_held(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = CheckoutSession(correlation_id="corr-unit", state=SessionState.CREATED)
    saga.sessions.save(session)
    saga.ihms.create_hold.return_value = HoldResponse(
        hold_id="hold-new",
        status=HoldStatus.ACTIVE,
        items=[HoldItemResponse(product_id="prod-widget-001", name="Widget", quantity=1)],
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    result = await saga.place_hold(
        session.session_id, "WIDGET-001", 1, "Jane Doe", obs
    )

    assert result.state == SessionState.HELD
    assert result.hold_id == "hold-new"
    assert len(result.line_items) == 1
    assert result.line_items[0].ihms_product_id == "prod-widget-001"


@pytest.mark.asyncio
async def test_concurrent_place_hold_creates_single_upstream_hold(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = CheckoutSession(correlation_id="corr-unit", state=SessionState.CREATED)
    saga.sessions.save(session)

    async def create_hold(*args, **kwargs) -> HoldResponse:
        await asyncio.sleep(0)
        return HoldResponse(
            hold_id="hold-race",
            status=HoldStatus.ACTIVE,
            items=[HoldItemResponse(product_id="prod-widget-001", name="Widget", quantity=1)],
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

    saga.ihms.create_hold.side_effect = create_hold

    results = await asyncio.gather(
        saga.place_hold(session.session_id, "WIDGET-001", 1, "Jane Doe", obs),
        saga.place_hold(session.session_id, "WIDGET-001", 1, "Jane Doe", obs),
        return_exceptions=True,
    )

    held = [result for result in results if isinstance(result, CheckoutSession)]
    errors = [result for result in results if isinstance(result, InvalidStateTransitionError)]
    assert len(held) == 1
    assert len(errors) == 1
    assert saga.ihms.create_hold.await_count == 1


@pytest.mark.asyncio
async def test_confirm_happy_path(saga: SagaCoordinator, obs: ObservabilityHeaders) -> None:
    session = _held_session()
    saga.sessions.save(session)
    order_id = uuid4()
    saga.ecops.create_order.return_value = OrderResponse(
        id=order_id,
        customer_name="Test Customer",
        status=OrderStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=None,
        items=[],
        client_reference="corr-unit",
    )

    result = await saga.confirm(session.session_id, None, "idem-1", obs)

    assert result.session.state == SessionState.CONFIRMED
    assert result.session.order_id == str(order_id)
    assert result.from_cache is False
    saga.ihms.fulfill_hold.assert_awaited_once_with("hold-1", obs)


@pytest.mark.asyncio
async def test_confirm_compensates_on_order_failure(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    saga.ecops.create_order.side_effect = UpstreamError(
        UpstreamProblem(status_code=500, detail="Order failed")
    )

    with pytest.raises(UpstreamError):
        await saga.confirm(session.session_id, None, "idem-2", obs)

    updated = saga.sessions.get(session.session_id)
    assert updated is not None
    assert updated.state == SessionState.COMPENSATED
    saga.ihms.release_hold.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_rejects_expired_hold(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    session = session.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)})
    saga.sessions.save(session)

    with pytest.raises(HoldExpiredError):
        await saga.confirm(session.session_id, None, "idem-3", obs)


@pytest.mark.asyncio
async def test_idempotency_returns_cached_response(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    order_id = uuid4()
    saga.ecops.create_order.return_value = OrderResponse(
        id=order_id,
        customer_name="Test Customer",
        status=OrderStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=None,
        items=[],
    )

    first = await saga.confirm(session.session_id, None, "idem-dup", obs)
    second = await saga.confirm(session.session_id, None, "idem-dup", obs)

    assert first.session.order_id == str(order_id)
    assert second.from_cache is True
    assert second.session.order_id == str(order_id)
    assert saga.ecops.create_order.await_count == 1


@pytest.mark.asyncio
async def test_idempotency_cache_retries_fulfill(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    order_id = uuid4()
    saga.ecops.create_order.return_value = OrderResponse(
        id=order_id,
        customer_name="Test Customer",
        status=OrderStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=None,
        items=[],
    )

    await saga.confirm(session.session_id, None, "idem-fulfill-retry", obs)
    saga.ihms.fulfill_hold.reset_mock()

    cached = await saga.confirm(session.session_id, None, "idem-fulfill-retry", obs)

    assert cached.from_cache is True
    saga.ihms.fulfill_hold.assert_awaited_once_with("hold-1", obs)


@pytest.mark.asyncio
async def test_confirm_with_pending_idempotency_key_skips_duplicate_order_post(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session().model_copy(update={"idempotency_key": "idem-pending"})
    saga.sessions.save(session)
    order_id = uuid4()
    saga.ecops.find_order_by_client_reference.return_value = OrderResponse(
        id=order_id,
        customer_name="Test Customer",
        status=OrderStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=None,
        items=[],
        client_reference="corr-unit",
    )

    result = await saga.confirm(session.session_id, None, "idem-pending", obs)

    assert result.session.state == SessionState.RECONCILED
    assert result.session.order_id == str(order_id)
    saga.ecops.create_order.assert_not_awaited()
    saga.ihms.fulfill_hold.assert_awaited_once_with("hold-1", obs)


@pytest.mark.asyncio
async def test_compensate_clears_idempotency_key(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    saga.ecops.create_order.side_effect = UpstreamError(
        UpstreamProblem(status_code=500, detail="Order failed")
    )

    with pytest.raises(UpstreamError):
        await saga.confirm(session.session_id, None, "idem-fail", obs)

    updated = saga.sessions.get(session.session_id)
    assert updated is not None
    assert updated.state == SessionState.COMPENSATED
    assert updated.idempotency_key is None


@pytest.mark.asyncio
async def test_confirm_skips_order_post_when_correlation_already_exists(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    order_id = uuid4()
    saga.ecops.find_order_by_client_reference.return_value = OrderResponse(
        id=order_id,
        customer_name="Test Customer",
        status=OrderStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=None,
        items=[],
        client_reference="corr-unit",
    )

    result = await saga.confirm(session.session_id, None, "idem-existing-order", obs)

    assert result.session.state == SessionState.RECONCILED
    assert result.session.order_id == str(order_id)
    saga.ecops.create_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_concurrent_duplicate_confirm_creates_single_order(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    order_id = uuid4()

    async def create_order(*args, **kwargs) -> OrderResponse:
        await asyncio.sleep(0)
        return OrderResponse(
            id=order_id,
            customer_name="Test Customer",
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=None,
            items=[],
            client_reference="corr-unit",
        )

    saga.ecops.create_order.side_effect = create_order

    first, second = await asyncio.gather(
        saga.confirm(session.session_id, None, "idem-race", obs),
        saga.confirm(session.session_id, None, "idem-race", obs),
    )

    assert {first.session.order_id, second.session.order_id} == {str(order_id)}
    assert sum(result.from_cache for result in (first, second)) == 1
    assert saga.ecops.create_order.await_count == 1


@pytest.mark.asyncio
async def test_reconcile_after_timeout(saga: SagaCoordinator, obs: ObservabilityHeaders) -> None:
    session = _held_session()
    saga.sessions.save(session)
    order_id = uuid4()
    saga.ecops.create_order.side_effect = GatewayTimeoutError("timeout")
    saga.ecops.find_order_by_client_reference.side_effect = [
        None,
        OrderResponse(
            id=order_id,
            customer_name="Test Customer",
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=None,
            items=[],
            client_reference="corr-unit",
        ),
    ]

    result = await saga.confirm(session.session_id, None, "idem-reconcile", obs)

    assert result.session.state == SessionState.RECONCILED
    assert result.session.order_id == str(order_id)
    saga.ihms.release_hold.assert_not_awaited()
    saga.ihms.fulfill_hold.assert_awaited_once_with("hold-1", obs)


@pytest.mark.asyncio
async def test_timeout_without_reconciled_order_does_not_retry_post(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    saga.ecops.create_order.side_effect = GatewayTimeoutError("timeout")
    saga.ecops.find_order_by_client_reference.return_value = None

    with pytest.raises(CompensationIncompleteError):
        await saga.confirm(session.session_id, None, "idem-timeout", obs)

    assert saga.ecops.create_order.await_count == 1
    saga.ihms.release_hold.assert_awaited_once_with("hold-1", obs)


@pytest.mark.asyncio
async def test_timeout_without_reconciled_order_does_not_requery_after_miss(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    saga.ecops.create_order.side_effect = GatewayTimeoutError("timeout")
    saga.ecops.find_order_by_client_reference.return_value = None

    with pytest.raises(CompensationIncompleteError):
        await saga.confirm(session.session_id, None, "idem-timeout-miss", obs)

    assert saga.ecops.find_order_by_client_reference.await_count == 4
    saga.ihms.release_hold.assert_awaited_once_with("hold-1", obs)
    updated = saga.sessions.get(session.session_id)
    assert updated is not None
    assert updated.state == SessionState.COMPENSATED


@pytest.mark.asyncio
async def test_confirm_transport_error_compensates_hold(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)
    saga.ecops.create_order.side_effect = GatewayError("connection reset")

    with pytest.raises(GatewayError):
        await saga.confirm(session.session_id, None, "idem-gateway-error", obs)

    saga.ihms.release_hold.assert_awaited_once_with("hold-1", obs)
    updated = saga.sessions.get(session.session_id)
    assert updated is not None
    assert updated.state == SessionState.COMPENSATED


@pytest.mark.asyncio
async def test_abandon_from_held_releases_hold(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.sessions.save(session)

    result = await saga.abandon(session.session_id, obs)

    assert result.state == SessionState.ABANDONED
    saga.ihms.release_hold.assert_awaited_once_with("hold-1", obs)


@pytest.mark.asyncio
async def test_confirm_rejects_non_held_state(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = CheckoutSession(correlation_id="corr-unit", state=SessionState.CREATED)
    saga.sessions.save(session)

    with pytest.raises(InvalidStateTransitionError):
        await saga.confirm(session.session_id, None, "idem-x", obs)


@pytest.mark.asyncio
async def test_place_hold_unknown_session_raises(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    with pytest.raises(SessionNotFoundError):
        await saga.place_hold(uuid4(), "WIDGET-001", 1, "Jane", obs)


@pytest.mark.asyncio
async def test_validate_hold_active_maps_409_to_expired(
    saga: SagaCoordinator, obs: ObservabilityHeaders
) -> None:
    session = _held_session()
    saga.ihms.get_hold.side_effect = HoldConflictError(
        UpstreamProblem(status_code=409, detail="Hold expired")
    )

    with pytest.raises(HoldExpiredError):
        await saga.validate_hold_active(session, obs)
