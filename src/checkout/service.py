"""Checkout workflow entry points."""

from dataclasses import dataclass
from uuid import UUID

from src.catalog.provider import CatalogProduct, CatalogProvider
from src.gateway.ecops_client import EcOpsClient
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient
from src.session.models import CheckoutSession, SessionState
from src.session.store import SessionStore


@dataclass
class CheckoutService:
    """Phase 2 checkout operations — session + catalog; saga flows in Phase 3."""

    catalog: CatalogProvider
    sessions: SessionStore
    ihms: IhmsClient
    ecops: EcOpsClient

    def create_session(self, correlation_id: str) -> CheckoutSession:
        session = CheckoutSession(correlation_id=correlation_id, state=SessionState.CREATED)
        return self.sessions.save(session)

    def get_session(self, session_id: UUID) -> CheckoutSession | None:
        return self.sessions.get(session_id)

    def list_catalog(self) -> list[CatalogProduct]:
        return self.catalog.list_products()

    def get_product(self, sku: str) -> CatalogProduct | None:
        return self.catalog.get_product(sku)

    @property
    def ihms_client(self) -> IhmsClient:
        """Expose gateway for component tests and Phase 3 saga wiring."""
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
