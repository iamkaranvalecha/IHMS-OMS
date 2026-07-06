"""Unified live IHMS catalog refresh — inventory (real main) or products (mock/plan-a)."""

import logging

from src.catalog.ecops_mapping import EcopsMapping
from src.catalog.ihms_cache import IhmsCatalogCache
from src.catalog.ihms_inventory import IhmsInventoryCatalogCache
from src.catalog.inventory import CatalogProductWithAvailability
from src.catalog.product_metadata import ProductMetadataCatalog
from src.gateway.exceptions import GatewayError
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient

logger = logging.getLogger(__name__)


class IhmsLiveCatalog:
    """Single cache surface for IHMS-backed catalog regardless of upstream endpoint."""

    def __init__(self) -> None:
        self._products_cache = IhmsCatalogCache()
        self._inventory_cache = IhmsInventoryCatalogCache()
        self._active: IhmsCatalogCache | IhmsInventoryCatalogCache | None = None
        self._source: str = "none"

    @property
    def source(self) -> str:
        return self._source

    async def refresh(
        self,
        ihms: IhmsClient,
        metadata: ProductMetadataCatalog,
        mapping: EcopsMapping,
        headers: ObservabilityHeaders,
        *,
        mode: str = "auto",
    ) -> None:
        if mode in ("auto", "products"):
            try:
                await self._products_cache.refresh(ihms, mapping, headers)
                if self._products_cache.list():
                    self._active = self._products_cache
                    self._source = "products"
                    return
            except GatewayError as exc:
                if mode == "products":
                    raise
                logger.debug("IHMS /api/products unavailable, trying inventory: %s", exc)

        await self._inventory_cache.refresh(ihms, metadata, mapping, headers)
        if not self._inventory_cache.list() and mode == "auto":
            raise GatewayError("IHMS catalog empty from both /api/products and /api/inventory")
        self._active = self._inventory_cache
        self._source = "inventory"

    def get(self, sku: str) -> CatalogProductWithAvailability | None:
        if self._active is None:
            return None
        return self._active.get(sku)

    def list(self) -> list[CatalogProductWithAvailability]:
        if self._active is None:
            return []
        return self._active.list()

    def load_from_json_catalog(
        self,
        json_catalog,
        mapping: EcopsMapping,
    ) -> None:
        self._products_cache.load_from_json_catalog(json_catalog, mapping)
        self._active = self._products_cache
        self._source = "json-fallback"


class IhmsLiveCatalogAdapter:
    """CatalogProvider backed by a refreshed IHMS live catalog cache."""

    def __init__(self, cache: IhmsLiveCatalog) -> None:
        self._cache = cache

    def get_product(self, sku: str):
        from src.catalog.provider import CatalogProduct

        enriched = self._cache.get(sku)
        if enriched is None:
            return None
        return CatalogProduct(
            sku=enriched.sku,
            name=enriched.name,
            ihms_product_id=enriched.ihms_product_id,
            ecops_item_code=enriched.ecops_item_code,
            unit_price=enriched.unit_price,
        )

    def list_products(self):
        from src.catalog.provider import CatalogProduct

        return [
            CatalogProduct(
                sku=p.sku,
                name=p.name,
                ihms_product_id=p.ihms_product_id,
                ecops_item_code=p.ecops_item_code,
                unit_price=p.unit_price,
            )
            for p in self._cache.list()
        ]
