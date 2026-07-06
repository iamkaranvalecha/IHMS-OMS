"""Live KB-IHMS inventory catalog — GET /api/inventory + orchestrator metadata."""

from src.catalog.ecops_mapping import EcopsMapping
from src.catalog.inventory import CatalogProductWithAvailability
from src.catalog.product_metadata import ProductMetadataCatalog
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient


class IhmsInventoryCatalogCache:
    """Refreshable catalog from IHMS GET /api/inventory (real KB-IHMS main API)."""

    def __init__(self) -> None:
        self._products: dict[str, CatalogProductWithAvailability] = {}

    async def refresh(
        self,
        ihms: IhmsClient,
        metadata: ProductMetadataCatalog,
        mapping: EcopsMapping,
        headers: ObservabilityHeaders,
    ) -> None:
        items = await ihms.get_inventory(headers)
        self._products = {}
        for item in items:
            meta = metadata.metadata_or_default(item.product_id, item.name)
            self._products[meta.sku] = CatalogProductWithAvailability(
                sku=meta.sku,
                name=item.name or meta.description or meta.sku,
                ihms_product_id=item.product_id,
                ecops_item_code=mapping.ecops_item_code(meta.sku),
                unit_price=meta.unit_price,
                available_quantity=item.available_quantity,
                description=meta.description or None,
                category=meta.category or None,
            )

    def get(self, sku: str) -> CatalogProductWithAvailability | None:
        return self._products.get(sku)

    def list(self) -> list[CatalogProductWithAvailability]:
        return list(self._products.values())
