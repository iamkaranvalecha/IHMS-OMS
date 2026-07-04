"""Saga coordinator — hold, confirm, abandon, compensation, reconciliation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.catalog.provider import CatalogProvider
from src.gateway.ecops_client import EcOpsClient
from src.gateway.ecops_models import OrderCreate, OrderItemCreate, OrderResponse
from src.gateway.exceptions import (
    GatewayTimeoutError,
    HoldConflictError,
    HoldNotFoundError,
    UpstreamError,
)
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient
from src.gateway.ihms_models import CreateHoldItemRequest
from src.saga.exceptions import (
    CompensationIncompleteError,
    HoldExpiredError,
    InvalidStateTransitionError,
    ProductNotFoundError,
    SessionNotFoundError,
)
from src.saga.idempotency import IdempotencyRecord, IdempotencyStore
from src.saga.steps.compensate import release_hold_safe
from src.saga.steps.reconcile import find_order_by_reference
from src.session.models import CheckoutSession, SessionLineItem, SessionState
from src.session.store import LockedSessionStore


@dataclass(frozen=True)
class ConfirmResult:
    """Outcome of a confirm saga step."""

    session: CheckoutSession
    from_cache: bool = False


@dataclass
class SagaCoordinator:
    """Orchestrates distributed checkout steps across IHMS and EC-OPS."""

    catalog: CatalogProvider
    sessions: LockedSessionStore
    ihms: IhmsClient
    ecops: EcOpsClient
    idempotency: IdempotencyStore

    async def place_hold(
        self,
        session_id: UUID,
        sku: str,
        quantity: int,
        customer_name: str,
        headers: ObservabilityHeaders,
    ) -> CheckoutSession:
        product = self.catalog.get_product(sku)
        if product is None:
            raise ProductNotFoundError(f"Product {sku} not found")

        line_item = SessionLineItem(
            sku=product.sku,
            name=product.name,
            ihms_product_id=product.ihms_product_id,
            ecops_item_code=product.ecops_item_code,
            quantity=quantity,
            unit_price=product.unit_price,
        )

        session = self.sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")
        if session.state != SessionState.CREATED:
            raise InvalidStateTransitionError(
                f"Cannot place hold from state {session.state.value}",
                detail=f"Session must be CREATED to place hold, got {session.state.value}",
            )

        hold_items = [
            CreateHoldItemRequest(product_id=line_item.ihms_product_id, quantity=line_item.quantity)
        ]
        hold = await self.ihms.create_hold(hold_items, headers)

        def apply_hold(current: CheckoutSession) -> CheckoutSession:
            if current.state != SessionState.CREATED:
                raise InvalidStateTransitionError(
                    f"Cannot place hold from state {current.state.value}",
                )
            return current.model_copy(
                update={
                    "state": SessionState.HELD,
                    "hold_id": hold.hold_id,
                    "expires_at": hold.expires_at,
                    "customer_name": customer_name,
                    "line_items": [line_item],
                }
            )

        return await self.sessions.mutate(session_id, apply_hold)

    async def confirm(
        self,
        session_id: UUID,
        customer_name: str | None,
        idempotency_key: str,
        headers: ObservabilityHeaders,
    ) -> ConfirmResult:
        cached = self.idempotency.get(session_id, idempotency_key)
        if cached is not None:
            session = self.sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError("Session not found")
            cached_state = cached.body.get("state")
            updates: dict[str, object] = {}
            if cached.order_id:
                updates["order_id"] = cached.order_id
            if cached_state and session.state == SessionState.HELD:
                updates["state"] = SessionState(str(cached_state))
            if updates:
                session = self.sessions.save(session.model_copy(update=updates))
            return ConfirmResult(session=session, from_cache=True)

        session = self.sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")
        if session.state != SessionState.HELD:
            raise InvalidStateTransitionError(
                f"Cannot confirm from state {session.state.value}",
                detail=f"Session must be HELD to confirm, got {session.state.value}",
            )
        if not session.line_items:
            raise InvalidStateTransitionError("Session has no line items to confirm")
        self._assert_hold_not_expired(session)

        resolved_customer = customer_name or session.customer_name
        if not resolved_customer:
            raise InvalidStateTransitionError("customer_name is required to confirm")

        order_payload = self._build_order_payload(session, resolved_customer)

        try:
            order, reconciled = await self._create_order_with_retry(
                order_payload,
                headers,
                idempotency_key=idempotency_key,
                client_reference=session.correlation_id,
            )
            terminal = SessionState.RECONCILED if reconciled else SessionState.CONFIRMED
            return await self._finalize_success(
                session_id,
                order,
                idempotency_key,
                terminal,
            )
        except UpstreamError:
            await self._compensate_and_fail(session_id, session, headers)
            raise
        except GatewayTimeoutError:
            order = await find_order_by_reference(
                self.ecops,
                session.correlation_id,
                headers,
            )
            if order is not None:
                return await self._finalize_success(
                    session_id,
                    order,
                    idempotency_key,
                    SessionState.RECONCILED,
                )
            await self._compensate_and_fail(session_id, session, headers)
            raise CompensationIncompleteError(
                "Order creation timed out and could not be reconciled; hold release attempted",
            ) from None

    async def abandon(
        self,
        session_id: UUID,
        headers: ObservabilityHeaders,
    ) -> CheckoutSession:
        session = self.sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")
        if session.is_terminal():
            raise InvalidStateTransitionError(
                f"Cannot abandon from terminal state {session.state.value}",
            )

        if session.state == SessionState.HELD and session.hold_id:
            released = await release_hold_safe(self.ihms, session.hold_id, headers)
            if not released:
                raise CompensationIncompleteError(
                    "Failed to release hold while abandoning checkout",
                )

        def apply_abandon(current: CheckoutSession) -> CheckoutSession:
            if current.is_terminal():
                raise InvalidStateTransitionError(
                    f"Cannot abandon from terminal state {current.state.value}",
                )
            return current.model_copy(update={"state": SessionState.ABANDONED})

        return await self.sessions.mutate(session_id, apply_abandon)

    async def _create_order_with_retry(
        self,
        payload: OrderCreate,
        headers: ObservabilityHeaders,
        *,
        idempotency_key: str,
        client_reference: str,
    ) -> tuple[OrderResponse, bool]:
        """Create order; return (order, reconciled_flag)."""
        payload = payload.model_copy(update={"client_reference": client_reference})
        try:
            order = await self.ecops.create_order(payload, headers, idempotency_key=idempotency_key)
            return order, False
        except GatewayTimeoutError:
            order = await find_order_by_reference(self.ecops, client_reference, headers)
            if order is not None:
                return order, True
            order = await self.ecops.create_order(payload, headers, idempotency_key=idempotency_key)
            return order, False

    async def _finalize_success(
        self,
        session_id: UUID,
        order: OrderResponse,
        idempotency_key: str,
        terminal_state: SessionState,
    ) -> ConfirmResult:
        order_id = str(order.id)

        def apply_success(current: CheckoutSession) -> CheckoutSession:
            if current.state != SessionState.HELD:
                raise InvalidStateTransitionError(
                    f"Cannot finalize confirm from state {current.state.value}",
                )
            return current.model_copy(
                update={
                    "state": terminal_state,
                    "order_id": order_id,
                    "idempotency_key": idempotency_key,
                }
            )

        session = await self.sessions.mutate(session_id, apply_success)
        body: dict[str, object] = {
            "session_id": str(session.session_id),
            "correlation_id": session.correlation_id,
            "state": session.state.value,
            "hold_id": session.hold_id,
            "order_id": order_id,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        }
        self.idempotency.put(
            session_id,
            idempotency_key,
            IdempotencyRecord(status_code=200, body=body, order_id=order_id),
        )
        return ConfirmResult(session=session)

    async def _compensate_and_fail(
        self,
        session_id: UUID,
        session: CheckoutSession,
        headers: ObservabilityHeaders,
    ) -> None:
        if not session.hold_id:
            return
        released = await release_hold_safe(self.ihms, session.hold_id, headers)
        if not released:
            raise CompensationIncompleteError(
                "Order failed but hold could not be released",
            )

        def apply_compensated(current: CheckoutSession) -> CheckoutSession:
            if current.state != SessionState.HELD:
                return current
            return current.model_copy(update={"state": SessionState.COMPENSATED})

        await self.sessions.mutate(session_id, apply_compensated)

    def _build_order_payload(self, session: CheckoutSession, customer_name: str) -> OrderCreate:
        items = [
            OrderItemCreate(
                product_name=item.ecops_item_code,
                quantity=item.quantity,
                price=Decimal(str(item.unit_price)),
            )
            for item in session.line_items
        ]
        return OrderCreate(
            customer_name=customer_name,
            items=items,
            client_reference=session.correlation_id,
        )

    def _assert_hold_not_expired(self, session: CheckoutSession) -> None:
        if session.expires_at is None:
            return
        if session.expires_at <= datetime.now(UTC):
            raise HoldExpiredError(
                "Hold expired before confirm",
                detail="Cannot confirm — hold TTL elapsed",
            )

    async def validate_hold_active(
        self,
        session: CheckoutSession,
        headers: ObservabilityHeaders,
    ) -> None:
        """Optional IHMS read to detect expiry (409) before confirm."""
        if not session.hold_id:
            return
        try:
            await self.ihms.get_hold(session.hold_id, headers)
        except HoldConflictError as exc:
            raise HoldExpiredError(
                "Hold expired before confirm",
                detail=exc.problem.detail,
            ) from exc
        except HoldNotFoundError as exc:
            raise HoldExpiredError(
                "Hold no longer available",
                detail=exc.problem.detail,
            ) from exc
