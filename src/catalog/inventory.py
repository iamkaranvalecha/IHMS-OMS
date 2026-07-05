"""Merge static catalog metadata with live KB-IHMS inventory."""

from pydantic import BaseModel, Field

from src.catalog.provider import CatalogProvider
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient


class CatalogProductWithAvailability(BaseModel):
    """Orchestrator catalog row enriched with IHMS stock."""

    sku: str
    name: str
    ihms_product_id: str = Field(description="KB-IHMS product identifier")
    ecops_item_code: str = Field(description="EC-OPS order line item code")
    unit_price: float
    available_quantity: int = Field(description="Units available to hold (from KB-IHMS)")


async def list_catalog_with_inventory(
    catalog: CatalogProvider,
    ihms: IhmsClient,
    headers: ObservabilityHeaders,
) -> list[CatalogProductWithAvailability]:
    """Join catalog SKUs with live available quantities from KB-IHMS."""
    inventory_by_product_id = {
        item.product_id: item.available_quantity
        for item in await ihms.get_inventory(headers)
    }
    return [
        CatalogProductWithAvailability(
            sku=product.sku,
            name=product.name,
            ihms_product_id=product.ihms_product_id,
            ecops_item_code=product.ecops_item_code,
            unit_price=product.unit_price,
            available_quantity=inventory_by_product_id.get(product.ihms_product_id, 0),
        )
        for product in catalog.list_products()
    ]
