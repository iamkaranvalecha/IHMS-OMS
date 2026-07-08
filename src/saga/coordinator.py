"""Saga coordinator — hold, confirm, abandon, compensation, reconciliation."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.catalog.provider import CatalogProvider
from src.gateway.ecops_client import EcOpsClient
from src.gateway.ecops_models import OrderCreate, OrderItemCreate, OrderResponse, OrderStatus
from src.gateway.exceptions import (
    GatewayError,
    GatewayTimeoutError,
    HoldConflictError,
    HoldNotFoundError,
    UpstreamError,
)
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient
from src.gateway.ihms_models import CreateHoldItemRequest
from src.observability.saga_events import (
    log_saga_step,
    record_abandon,
    record_compensation,
    record_confirm_success,
    record_hold_failed,
    record_hold_placed,
    record_order_status_unknown,
)
from src.saga.exceptions import (
    CompensationIncompleteError,
    HoldExpiredError,
    InsufficientStockError,
    InvalidStateTransitionError,
    OrderStatusUnknownError,
    ProductNotFoundError,
    SessionNotFoundError,
)
from src.saga.idempotency import IdempotencyRecord, IdempotencyStore
from src.saga.steps.compensate import release_hold_safe
from src.saga.steps.finalize import fulfill_hold_safe
from src.saga.steps.reconcile import find_order_by_reference
from src.session.models import CheckoutSession, SessionLineItem, SessionState
from src.session.store import LockedSessionStore


@dataclass(frozen=True)
class ConfirmResult:
    """Outcome of a confirm saga step."""

    session: CheckoutSession
    from_cache: bool = False


@dataclass(frozen=True)
class PlaceOrderResult:
    """Outcome of atomic place-order (hold + EC-OPS order + finalize)."""

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
        items: list[tuple[str, int]],
        customer_name: str,
        headers: ObservabilityHeaders,
    ) -> CheckoutSession:
        if not items:
            raise InvalidStateTransitionError(
                "Cannot place hold with an empty cart",
                detail="At least one line item is required",
            )

        merged_quantities: dict[str, int] = {}
        for sku, quantity in items:
            merged_quantities[sku] = merged_quantities.get(sku, 0) + quantity

        line_items: list[SessionLineItem] = []
        for sku, quantity in merged_quantities.items():
            product = self.catalog.get_product(sku)
            if product is None:
                raise ProductNotFoundError(f"Product {sku} not found")
            line_items.append(
                SessionLineItem(
                    sku=product.sku,
                    name=product.name,
                    ihms_product_id=product.ihms_product_id,
                    ecops_item_code=product.ecops_item_code,
                    quantity=quantity,
                    unit_price=product.unit_price,
                )
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
            CreateHoldItemRequest(product_id=item.ihms_product_id, quantity=item.quantity)
            for item in line_items
        ]
        async with self.sessions.lock_for(session_id):
            session = self.sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError("Session not found")
            if session.state != SessionState.CREATED:
                raise InvalidStateTransitionError(
                    f"Cannot place hold from state {session.state.value}",
                )

            await self._assert_sufficient_stock_for_lines(line_items, headers)

            try:
                hold = await self.ihms.create_hold(hold_items, headers)
            except (HoldConflictError, UpstreamError):
                record_hold_failed()
                log_saga_step(
                    "place_hold",
                    "hold rejected by upstream",
                    level=logging.WARNING,
                    session_id=session_id,
                    outcome="failed",
                )
                raise
            updated = session.model_copy(
                update={
                    "state": SessionState.HELD,
                    "hold_id": hold.hold_id,
                    "expires_at": hold.expires_at,
                    "customer_name": customer_name,
                    "line_items": line_items,
                }
            )
            saved = self.sessions.save(updated)
            record_hold_placed()
            log_saga_step(
                "place_hold",
                "hold placed",
                session_id=session_id,
                hold_id=hold.hold_id,
                outcome="success",
            )
            return saved

    async def confirm(
        self,
        session_id: UUID,
        customer_name: str | None,
        idempotency_key: str,
        headers: ObservabilityHeaders,
    ) -> ConfirmResult:
        async with self.sessions.lock_for(session_id):
            cached = self.idempotency.get(session_id, idempotency_key)
            if cached is not None:
                session = self.sessions.get(session_id)
                if session is None:
                    raise SessionNotFoundError("Session not found")
                cached_state = cached.body.get("state")
                updates: dict[str, object] = {}
                if cached.order_id:
                    updates["order_id"] = cached.order_id
                if cached_state and session.state in (
                    SessionState.HELD,
                    SessionState.FULFILL_PENDING,
                ):
                    updates["state"] = SessionState(str(cached_state))
                if updates:
                    session = self.sessions.save(session.model_copy(update=updates))
                if session.state == SessionState.FULFILL_PENDING:
                    return await self._retry_fulfill_pending_locked(
                        session,
                        idempotency_key,
                        headers,
                        from_cache=True,
                    )
                if session.hold_id and session.is_terminal():
                    await fulfill_hold_safe(self.ihms, session.hold_id, headers)
                log_saga_step(
                    "confirm",
                    "confirm served from idempotency cache",
                    session_id=session_id,
                    order_id=session.order_id,
                    outcome="cached",
                )
                return ConfirmResult(session=session, from_cache=True)

            session = self.sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError("Session not found")
            if session.state == SessionState.FULFILL_PENDING:
                if session.idempotency_key != idempotency_key:
                    raise InvalidStateTransitionError(
                        "Retry fulfill with the original Idempotency-Key",
                        detail="Order was placed but hold finalization is pending",
                    )
                return await self._retry_fulfill_pending_locked(
                    session,
                    idempotency_key,
                    headers,
                )
            if session.state != SessionState.HELD:
                raise InvalidStateTransitionError(
                    f"Cannot confirm from state {session.state.value}",
                    detail=f"Session must be HELD to confirm, got {session.state.value}",
                )
            if session.idempotency_key is not None:
                if session.idempotency_key != idempotency_key:
                    raise InvalidStateTransitionError(
                        "Confirm already has an unresolved order attempt",
                        detail="Retry with the original Idempotency-Key to resolve order status",
                    )
                return await self._resolve_existing_order_attempt_locked(
                    session,
                    headers,
                    idempotency_key,
                )
            if not session.line_items:
                raise InvalidStateTransitionError("Session has no line items to confirm")
            self._assert_hold_not_expired(session)

            resolved_customer = customer_name or session.customer_name
            if not resolved_customer:
                raise InvalidStateTransitionError("customer_name is required to confirm")

            order_payload = self._build_order_payload(session, resolved_customer)

            try:
                existing_order = await find_order_by_reference(
                    self.ecops,
                    session.correlation_id,
                    headers,
                    max_retries=0,
                )
                if existing_order is not None:
                    order, reconciled = existing_order, True
                else:
                    order, reconciled = await self._create_order_with_retry(
                        order_payload,
                        headers,
                        idempotency_key=idempotency_key,
                        client_reference=session.correlation_id,
                    )
                return await self._complete_order_after_create_locked(
                    session,
                    order,
                    idempotency_key,
                    headers,
                    reconciled=reconciled,
                )
            except UpstreamError:
                await self._compensate_and_fail_locked(session, headers)
                raise
            except GatewayTimeoutError:
                await self._compensate_and_fail_locked(session, headers)
                raise CompensationIncompleteError(
                    "Order creation timed out and could not be reconciled; hold release attempted",
                ) from None
            except OrderStatusUnknownError:
                self.sessions.save(session.model_copy(update={"idempotency_key": idempotency_key}))
                record_order_status_unknown()
                log_saga_step(
                    "confirm",
                    "order status unknown after timeout",
                    level=logging.WARNING,
                    session_id=session_id,
                    hold_id=session.hold_id,
                    outcome="unknown",
                )
                raise
            except GatewayError:
                await self._compensate_and_fail_locked(session, headers)
                raise

    async def abandon(
        self,
        session_id: UUID,
        headers: ObservabilityHeaders,
    ) -> CheckoutSession:
        async with self.sessions.lock_for(session_id):
            session = self.sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError("Session not found")
            if session.is_terminal():
                raise InvalidStateTransitionError(
                    f"Cannot abandon from terminal state {session.state.value}",
                )
            if session.state == SessionState.FULFILL_PENDING:
                raise InvalidStateTransitionError(
                    "Cannot abandon while order is placed and hold fulfill is pending",
                    detail="Retry confirm with the same Idempotency-Key to finalize the hold",
                )

            if session.state == SessionState.HELD and session.hold_id:
                released = await release_hold_safe(self.ihms, session.hold_id, headers)
                if not released:
                    raise CompensationIncompleteError(
                        "Failed to release hold while abandoning checkout",
                    )

            saved = self.sessions.save(session.model_copy(update={"state": SessionState.ABANDONED}))
            record_abandon()
            log_saga_step(
                "abandon",
                "checkout abandoned",
                session_id=session_id,
                hold_id=session.hold_id,
                outcome="abandoned",
            )
            return saved

    async def place_order(
        self,
        session_id: UUID,
        items: list[tuple[str, int]],
        customer_name: str,
        idempotency_key: str,
        headers: ObservabilityHeaders,
    ) -> PlaceOrderResult:
        """Idempotent atomic checkout — hold once, then EC-OPS order + finalize."""
        cached = self.idempotency.get(session_id, idempotency_key)
        if cached is not None:
            session = self.sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError("Session not found")
            cached_state = cached.body.get("state")
            updates: dict[str, object] = {}
            if cached.order_id:
                updates["order_id"] = cached.order_id
            if cached_state and session.state in (
                SessionState.CREATED,
                SessionState.HELD,
                SessionState.FULFILL_PENDING,
            ):
                updates["state"] = SessionState(str(cached_state))
            if updates:
                session = self.sessions.save(session.model_copy(update=updates))
            log_saga_step(
                "place_order",
                "place-order served from idempotency cache",
                session_id=session_id,
                order_id=session.order_id,
                outcome="cached",
            )
            return PlaceOrderResult(session=session, from_cache=True)

        session = self.sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")
        if session.is_terminal():
            raise InvalidStateTransitionError(
                f"Cannot place order from terminal state {session.state.value}",
            )

        resolved_customer = customer_name.strip() or session.customer_name or "Guest"

        if session.state == SessionState.CREATED:
            log_saga_step(
                "place_order",
                "placing IHMS hold",
                session_id=session_id,
                correlation_id=session.correlation_id,
                trace_id=headers.trace_id,
                outcome="hold_start",
            )
            session = await self.place_hold(
                session_id,
                items,
                resolved_customer,
                headers,
            )

        session = self.sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")

        if session.state == SessionState.FULFILL_PENDING:
            confirm = await self.confirm(session_id, resolved_customer, idempotency_key, headers)
            return PlaceOrderResult(session=confirm.session, from_cache=confirm.from_cache)

        if session.state != SessionState.HELD:
            raise InvalidStateTransitionError(
                f"Cannot place order from state {session.state.value}",
            )

        log_saga_step(
            "place_order",
            "creating EC-OPS order",
            session_id=session_id,
            correlation_id=session.correlation_id,
            trace_id=headers.trace_id,
            hold_id=session.hold_id,
            outcome="order_start",
        )
        confirm = await self.confirm(session_id, resolved_customer, idempotency_key, headers)
        return PlaceOrderResult(session=confirm.session, from_cache=confirm.from_cache)

    async def _create_order_with_retry(
        self,
        payload: OrderCreate,
        headers: ObservabilityHeaders,
        *,
        idempotency_key: str,
        client_reference: str,
    ) -> tuple[OrderResponse, bool]:
        """Create order; return (order, reconciled_flag)."""
        try:
            order = await self.ecops.create_order(payload, headers, idempotency_key=idempotency_key)
            return order, False
        except UpstreamError as exc:
            if exc.problem.status_code == 409:
                order = await find_order_by_reference(self.ecops, client_reference, headers)
                if order is not None:
                    return order, True
            raise
        except GatewayTimeoutError as create_timeout:
            try:
                order = await find_order_by_reference(self.ecops, client_reference, headers)
            except GatewayError as exc:
                raise OrderStatusUnknownError(
                    "Order creation timed out and reconciliation failed; hold retained",
                    detail="Order status is unknown; hold was not released",
                ) from exc
            if order is not None:
                return order, True
            raise create_timeout

    def _finalize_success_locked(
        self,
        session: CheckoutSession,
        order: OrderResponse,
        idempotency_key: str,
        terminal_state: SessionState,
    ) -> ConfirmResult:
        order_id = str(order.id)
        if session.state not in (SessionState.HELD, SessionState.FULFILL_PENDING):
            raise InvalidStateTransitionError(
                f"Cannot finalize confirm from state {session.state.value}",
            )
        session = self.sessions.save(
            session.model_copy(
                update={
                    "state": terminal_state,
                    "order_id": order_id,
                    "idempotency_key": idempotency_key,
                }
            )
        )
        body: dict[str, object] = {
            "session_id": str(session.session_id),
            "correlation_id": session.correlation_id,
            "state": session.state.value,
            "hold_id": session.hold_id,
            "order_id": order_id,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        }
        self.idempotency.put(
            session.session_id,
            idempotency_key,
            IdempotencyRecord(status_code=200, body=body, order_id=order_id),
        )
        return ConfirmResult(session=session)

    async def _resolve_existing_order_attempt_locked(
        self,
        session: CheckoutSession,
        headers: ObservabilityHeaders,
        idempotency_key: str,
    ) -> ConfirmResult:
        """Resolve a prior ambiguous order create before considering another POST."""
        try:
            order = await find_order_by_reference(self.ecops, session.correlation_id, headers)
        except GatewayError as exc:
            raise OrderStatusUnknownError(
                "Previous order status is still unknown; hold retained",
                detail="Order status is unknown; hold was not released",
            ) from exc
        if order is not None:
            return await self._complete_order_after_create_locked(
                session,
                order,
                idempotency_key,
                headers,
                reconciled=True,
            )

        raise OrderStatusUnknownError(
            "Previous order attempt was not found; hold retained",
            detail="Order status is unknown; hold was not released",
        )

    async def _complete_order_after_create_locked(
        self,
        session: CheckoutSession,
        order: OrderResponse,
        idempotency_key: str,
        headers: ObservabilityHeaders,
        *,
        reconciled: bool,
    ) -> ConfirmResult:
        order_id = str(order.id)
        fulfilled = True
        if session.hold_id:
            fulfilled = await fulfill_hold_safe(self.ihms, session.hold_id, headers)

        if not fulfilled:
            pending = self.sessions.save(
                session.model_copy(
                    update={
                        "state": SessionState.FULFILL_PENDING,
                        "order_id": order_id,
                        "idempotency_key": idempotency_key,
                    }
                )
            )
            self._cache_confirm_response(pending, idempotency_key, SessionState.FULFILL_PENDING)
            log_saga_step(
                "confirm",
                "order placed; hold fulfill pending",
                level=logging.WARNING,
                session_id=pending.session_id,
                hold_id=pending.hold_id,
                order_id=order_id,
                outcome="fulfill_pending",
            )
            return ConfirmResult(session=pending)

        terminal = SessionState.RECONCILED if reconciled else SessionState.CONFIRMED
        result = self._finalize_success_locked(session, order, idempotency_key, terminal)
        record_confirm_success(reconciled=reconciled)
        log_saga_step(
            "reconcile" if reconciled else "confirm",
            "checkout confirmed",
            session_id=session.session_id,
            hold_id=result.session.hold_id,
            order_id=result.session.order_id,
            outcome=terminal.value.lower(),
        )
        return result

    async def _retry_fulfill_pending_locked(
        self,
        session: CheckoutSession,
        idempotency_key: str,
        headers: ObservabilityHeaders,
        *,
        from_cache: bool = False,
    ) -> ConfirmResult:
        if not session.hold_id or not session.order_id:
            raise InvalidStateTransitionError(
                "Fulfill pending session is missing hold or order identifiers",
            )
        fulfilled = await fulfill_hold_safe(self.ihms, session.hold_id, headers)
        if not fulfilled:
            log_saga_step(
                "confirm",
                "hold fulfill still pending",
                level=logging.WARNING,
                session_id=session.session_id,
                hold_id=session.hold_id,
                order_id=session.order_id,
                outcome="fulfill_pending",
            )
            return ConfirmResult(session=session, from_cache=from_cache)

        order = OrderResponse(
            id=UUID(session.order_id),
            customer_name=session.customer_name or "",
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=None,
            items=[],
        )
        result = self._finalize_success_locked(
            session,
            order,
            idempotency_key,
            SessionState.CONFIRMED,
        )
        record_confirm_success(reconciled=False)
        log_saga_step(
            "confirm",
            "hold fulfill completed after pending",
            session_id=session.session_id,
            hold_id=result.session.hold_id,
            order_id=result.session.order_id,
            outcome="confirmed",
        )
        return ConfirmResult(session=result.session, from_cache=from_cache)

    def _cache_confirm_response(
        self,
        session: CheckoutSession,
        idempotency_key: str,
        state: SessionState,
    ) -> None:
        body: dict[str, object] = {
            "session_id": str(session.session_id),
            "correlation_id": session.correlation_id,
            "state": state.value,
            "hold_id": session.hold_id,
            "order_id": session.order_id,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        }
        self.idempotency.put(
            session.session_id,
            idempotency_key,
            IdempotencyRecord(status_code=200, body=body, order_id=session.order_id),
        )

    async def _assert_sufficient_stock_for_lines(
        self,
        line_items: list[SessionLineItem],
        headers: ObservabilityHeaders,
    ) -> None:
        try:
            inventory = await self.ihms.get_inventory(headers)
        except GatewayError:
            return
        inventory_by_product_id = {
            item.product_id: item.available_quantity for item in inventory
        }
        for line_item in line_items:
            available = inventory_by_product_id.get(line_item.ihms_product_id, 0)
            if line_item.quantity > available:
                raise InsufficientStockError(
                    f"Only {available} units available for {line_item.sku}",
                    detail=(
                        f"Requested {line_item.quantity} of {line_item.sku}, "
                        f"but only {available} available after existing holds"
                    ),
                )

    async def _compensate_and_fail_locked(
        self,
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

        if session.state == SessionState.HELD:
            self.sessions.save(
                session.model_copy(
                    update={"state": SessionState.COMPENSATED, "idempotency_key": None}
                )
            )

        record_compensation()
        log_saga_step(
            "compensate",
            "hold released after order failure",
            session_id=session.session_id,
            hold_id=session.hold_id,
            outcome="compensated",
        )

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
            client_reference=session.correlation_id,
            items=items,
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
