"""Checkout workflow entry points."""

import logging
from dataclasses import dataclass
from uuid import UUID

from src.catalog.ecops_mapping import EcopsMapping
from src.catalog.ihms_live import IhmsLiveCatalog
from src.catalog.inventory import (
    CatalogProductWithAvailability,
    get_product_with_inventory,
    list_catalog_with_inventory,
)
from src.catalog.product_metadata import ProductMetadataCatalog
from src.catalog.provider import CatalogProduct, CatalogProvider, JsonCatalogProvider
from src.gateway.ecops_client import EcOpsClient
from src.gateway.exceptions import GatewayError
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient
from src.saga.coordinator import ConfirmResult, PlaceOrderResult, SagaCoordinator
from src.saga.idempotency import IdempotencyStore, InMemoryIdempotencyStore
from src.session.models import CheckoutSession, SessionState
from src.session.store import LockedSessionStore, SessionStore
from src.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class CheckoutService:
    """Checkout operations — session, catalog, and saga flows."""

    catalog: CatalogProvider
    sessions: LockedSessionStore
    ihms: IhmsClient
    ecops: EcOpsClient
    idempotency: IdempotencyStore
    saga: SagaCoordinator
    ihms_live_catalog: IhmsLiveCatalog | None = None
    product_metadata: ProductMetadataCatalog | None = None
    ecops_mapping: EcopsMapping | None = None
    json_catalog_fallback: JsonCatalogProvider | None = None
    settings: Settings | None = None

    @classmethod
    def create(
        cls,
        *,
        catalog: CatalogProvider,
        sessions: SessionStore,
        ihms: IhmsClient,
        ecops: EcOpsClient,
        idempotency: IdempotencyStore | None = None,
        ihms_live_catalog: IhmsLiveCatalog | None = None,
        product_metadata: ProductMetadataCatalog | None = None,
        ecops_mapping: EcopsMapping | None = None,
        json_catalog_fallback: JsonCatalogProvider | None = None,
        settings: Settings | None = None,
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
            ihms_live_catalog=ihms_live_catalog,
            product_metadata=product_metadata,
            ecops_mapping=ecops_mapping,
            json_catalog_fallback=json_catalog_fallback,
            settings=settings,
        )

    def _fallback_enabled(self) -> bool:
        return (
            self.json_catalog_fallback is not None
            and (self.settings is None or self.settings.catalog_fallback_to_json)
        )

    def _ihms_unreachable_message(self, exc: GatewayError) -> GatewayError:
        base_url = self.settings.ihms_base_url if self.settings else "IHMS"
        return GatewayError(
            f"Cannot reach KB-IHMS at {base_url}. "
            "For mock stack run: bash scripts/mock-stack.sh. "
            "For real KB-IHMS run: bash scripts/real-upstream.sh "
            f"(detail: {exc})"
        )

    async def _refresh_ihms_catalog(self, headers: ObservabilityHeaders) -> None:
        if (
            self.ihms_live_catalog is None
            or self.ecops_mapping is None
            or self.product_metadata is None
        ):
            return
        mode = self.settings.ihms_catalog_mode if self.settings else "auto"
        try:
            await self.ihms_live_catalog.refresh(
                self.ihms,
                self.product_metadata,
                self.ecops_mapping,
                headers,
                mode=mode,
            )
        except GatewayError as exc:
            if self._fallback_enabled():
                logger.warning(
                    "IHMS catalog unavailable at %s; using JSON catalog fallback",
                    self.settings.ihms_base_url if self.settings else "IHMS",
                )
                self.ihms_live_catalog.load_from_json_catalog(
                    self.json_catalog_fallback,
                    self.ecops_mapping,
                )
                return
            raise self._ihms_unreachable_message(exc) from exc

    def _json_catalog_without_stock(self) -> list[CatalogProductWithAvailability]:
        if self.json_catalog_fallback is None or self.ecops_mapping is None:
            return []
        return [
            CatalogProductWithAvailability(
                sku=product.sku,
                name=product.name,
                ihms_product_id=product.ihms_product_id,
                ecops_item_code=self.ecops_mapping.ecops_item_code(product.sku),
                unit_price=product.unit_price,
                available_quantity=None,
            )
            for product in self.json_catalog_fallback.list_products()
        ]

    def create_session(self, correlation_id: str) -> CheckoutSession:
        session = CheckoutSession(correlation_id=correlation_id, state=SessionState.CREATED)
        return self.sessions.save(session)

    def get_session(self, session_id: UUID) -> CheckoutSession | None:
        return self.sessions.get(session_id)

    def list_catalog(self) -> list[CatalogProduct]:
        return self.catalog.list_products()

    def get_product(self, sku: str) -> CatalogProduct | None:
        return self.catalog.get_product(sku)

    async def list_catalog_with_inventory(
        self,
        headers: ObservabilityHeaders,
    ) -> list[CatalogProductWithAvailability]:
        if self.ihms_live_catalog is not None and self.ecops_mapping is not None:
            await self._refresh_ihms_catalog(headers)
            products = self.ihms_live_catalog.list()
            if products:
                return products
            if self._fallback_enabled():
                logger.warning("IHMS catalog empty; falling back to JSON catalog")
                try:
                    return await list_catalog_with_inventory(
                        self.json_catalog_fallback,
                        self.ihms,
                        headers,
                        allow_degraded=True,
                    )
                except GatewayError:
                    return self._json_catalog_without_stock()
            return products
        return await list_catalog_with_inventory(self.catalog, self.ihms, headers)

    async def get_product_with_inventory(
        self,
        sku: str,
        headers: ObservabilityHeaders,
    ) -> CatalogProductWithAvailability | None:
        if self.ihms_live_catalog is not None and self.ecops_mapping is not None:
            await self._refresh_ihms_catalog(headers)
            product = self.ihms_live_catalog.get(sku)
            if product is not None:
                return product
            if self._fallback_enabled():
                return await get_product_with_inventory(
                    self.json_catalog_fallback,
                    self.ihms,
                    sku,
                    headers,
                    allow_degraded=True,
                )
            return None
        return await get_product_with_inventory(self.catalog, self.ihms, sku, headers)

    async def place_hold(
        self,
        session_id: UUID,
        items: list[tuple[str, int]],
        customer_name: str,
        headers: ObservabilityHeaders,
    ) -> CheckoutSession:
        if self.ihms_live_catalog is not None and self.ecops_mapping is not None:
            await self._refresh_ihms_catalog(headers)
            if not self.ihms_live_catalog.list() and not self._fallback_enabled():
                raise self._ihms_unreachable_message(
                    GatewayError("IHMS catalog is empty and JSON fallback is disabled")
                )
        return await self.saga.place_hold(session_id, items, customer_name, headers)

    async def place_order(
        self,
        session_id: UUID,
        items: list[tuple[str, int]],
        customer_name: str,
        idempotency_key: str,
        headers: ObservabilityHeaders,
    ) -> PlaceOrderResult:
        """Atomic checkout: IHMS hold → EC-OPS PENDING order → inventory finalize."""
        if self.ihms_live_catalog is not None and self.ecops_mapping is not None:
            await self._refresh_ihms_catalog(headers)
            if not self.ihms_live_catalog.list() and not self._fallback_enabled():
                raise self._ihms_unreachable_message(
                    GatewayError("IHMS catalog is empty and JSON fallback is disabled")
                )
        return await self.saga.place_order(
            session_id,
            items,
            customer_name,
            idempotency_key,
            headers,
        )

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
            and session.state in (SessionState.HELD, SessionState.FULFILL_PENDING)
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
