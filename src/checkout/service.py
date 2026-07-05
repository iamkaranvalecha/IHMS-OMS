"""Checkout workflow entry points."""

from dataclasses import dataclass
from uuid import UUID

from src.catalog.inventory import CatalogProductWithAvailability, list_catalog_with_inventory
from src.catalog.provider import CatalogProduct, CatalogProvider
from src.gateway.ecops_client import EcOpsClient
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient
from src.saga.coordinator import ConfirmResult, SagaCoordinator
from src.saga.idempotency import IdempotencyStore, InMemoryIdempotencyStore
from src.session.models import CheckoutSession, SessionState
from src.session.store import LockedSessionStore, SessionStore


@dataclass
class CheckoutService:
    """Checkout operations — session, catalog, and saga flows."""

    catalog: CatalogProvider
    sessions: LockedSessionStore
    ihms: IhmsClient
    ecops: EcOpsClient
    idempotency: IdempotencyStore
    saga: SagaCoordinator

    @classmethod
    def create(
        cls,
        *,
        catalog: CatalogProvider,
        sessions: SessionStore,
        ihms: IhmsClient,
        ecops: EcOpsClient,
        idempotency: IdempotencyStore | None = None,
    ) -> "CheckoutService":
        if isinstance(sessions, LockedSessionStore):
            locked = sessions
        else:
            locked = LockedSessionStore(sessions)
        idem = idempotency or InMemoryIdempotencyStore()
        saga = SagaCoordinator(
            catalog=catalog,
            sessions=locked,
            ihms=ihms,
            ecops=ecops,
            idempotency=idem,
        )
        return cls(
            catalog=catalog,
            sessions=locked,
            ihms=ihms,
            ecops=ecops,
            idempotency=idem,
            saga=saga,
        )

    def create_session(self, correlation_id: str) -> CheckoutSession:
        session = CheckoutSession(correlation_id=correlation_id, state=SessionState.CREATED)
        return self.sessions.save(session)

    def get_session(self, session_id: UUID) -> CheckoutSession | None:
        return self.sessions.get(session_id)

    def list_catalog(self) -> list[CatalogProduct]:
        return self.catalog.list_products()

    async def list_catalog_with_inventory(
        self,
        headers: ObservabilityHeaders,
    ) -> list[CatalogProductWithAvailability]:
        return await list_catalog_with_inventory(self.catalog, self.ihms, headers)

    def get_product(self, sku: str) -> CatalogProduct | None:
        return self.catalog.get_product(sku)

    async def place_hold(
        self,
        session_id: UUID,
        sku: str,
        quantity: int,
        customer_name: str,
        headers: ObservabilityHeaders,
    ) -> CheckoutSession:
        return await self.saga.place_hold(session_id, sku, quantity, customer_name, headers)

    async def confirm(
        self,
        session_id: UUID,
        customer_name: str | None,
        idempotency_key: str,
        headers: ObservabilityHeaders,
    ) -> ConfirmResult:
        session = self.sessions.get(session_id)
        if (
            session is not None
            and session.state == SessionState.HELD
            and session.idempotency_key is None
        ):
            await self.saga.validate_hold_active(session, headers)
        return await self.saga.confirm(session_id, customer_name, idempotency_key, headers)

    async def abandon(
        self,
        session_id: UUID,
        headers: ObservabilityHeaders,
    ) -> CheckoutSession:
        return await self.saga.abandon(session_id, headers)

    @property
    def ihms_client(self) -> IhmsClient:
        return self.ihms

    @property
    def ecops_client(self) -> EcOpsClient:
        return self.ecops

    def observability_from_request(
        self,
        request_id: str,
        correlation_id: str,
        trace_id: str,
    ) -> ObservabilityHeaders:
        return ObservabilityHeaders(
            request_id=request_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    def observability_for_session(
        self,
        session: CheckoutSession,
        request_id: str,
        trace_id: str,
    ) -> ObservabilityHeaders:
        """Outbound headers for saga steps — session correlation spans the checkout."""
        return ObservabilityHeaders(
            request_id=request_id,
            correlation_id=session.correlation_id,
            trace_id=trace_id,
        )
