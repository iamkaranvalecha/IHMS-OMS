"""Live KB-IHMS product catalog cache for checkout."""

from src.catalog.ecops_mapping import EcopsMapping
from src.catalog.inventory import CatalogProductWithAvailability
from src.catalog.provider import CatalogProduct
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient
from src.gateway.ihms_models import ProductCatalogItemResponse


class IhmsCatalogCache:
    """Refreshable view of IHMS GET /api/products joined with EC-OPS mapping."""

    def __init__(self) -> None:
        self._products: dict[str, CatalogProductWithAvailability] = {}

    async def refresh(
        self,
        ihms: IhmsClient,
        mapping: EcopsMapping,
        headers: ObservabilityHeaders,
    ) -> None:
        items = await ihms.get_products(headers)
        self._products = {
            product.sku: _to_enriched(product, mapping)
            for product in items
            if product.sellable
        }

    def get(self, sku: str) -> CatalogProductWithAvailability | None:
        return self._products.get(sku)

    def list(self) -> list[CatalogProductWithAvailability]:
        return list(self._products.values())


class IhmsCatalogAdapter:
    """CatalogProvider backed by a refreshed IHMS catalog cache."""

    def __init__(self, cache: IhmsCatalogCache) -> None:
        self._cache = cache

    def get_product(self, sku: str) -> CatalogProduct | None:
        enriched = self._cache.get(sku)
        if enriched is None:
            return None
        return _to_catalog_product(enriched)

    def list_products(self) -> list[CatalogProduct]:
        return [_to_catalog_product(product) for product in self._cache.list()]


def _to_enriched(
    product: ProductCatalogItemResponse,
    mapping: EcopsMapping,
) -> CatalogProductWithAvailability:
    return CatalogProductWithAvailability(
        sku=product.sku,
        name=product.name,
        ihms_product_id=product.product_id,
        ecops_item_code=mapping.ecops_item_code(product.sku),
        unit_price=float(product.unit_price),
        available_quantity=product.available_quantity,
        description=product.description or None,
        image_url=product.image_url or None,
        category=product.category or None,
    )


def _to_catalog_product(enriched: CatalogProductWithAvailability) -> CatalogProduct:
    return CatalogProduct(
        sku=enriched.sku,
        name=enriched.name,
        ihms_product_id=enriched.ihms_product_id,
        ecops_item_code=enriched.ecops_item_code,
        unit_price=enriched.unit_price,
    )
