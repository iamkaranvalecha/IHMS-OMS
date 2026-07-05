"""Merge static catalog metadata with live KB-IHMS inventory."""

import logging

from pydantic import BaseModel, Field

from src.catalog.provider import CatalogProvider
from src.gateway.exceptions import GatewayError
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient

logger = logging.getLogger(__name__)


class CatalogProductWithAvailability(BaseModel):
    """Orchestrator catalog row enriched with IHMS stock."""

    sku: str
    name: str
    ihms_product_id: str = Field(description="KB-IHMS product identifier")
    ecops_item_code: str = Field(description="EC-OPS order line item code")
    unit_price: float
    available_quantity: int | None = Field(
        default=None,
        description="Units available to hold (from KB-IHMS); null when stock unknown",
    )


def _catalog_without_inventory(catalog: CatalogProvider) -> list[CatalogProductWithAvailability]:
    return [
        CatalogProductWithAvailability(
            sku=product.sku,
            name=product.name,
            ihms_product_id=product.ihms_product_id,
            ecops_item_code=product.ecops_item_code,
            unit_price=product.unit_price,
            available_quantity=None,
        )
        for product in catalog.list_products()
    ]


async def list_catalog_with_inventory(
    catalog: CatalogProvider,
    ihms: IhmsClient,
    headers: ObservabilityHeaders,
    *,
    allow_degraded: bool = True,
) -> list[CatalogProductWithAvailability]:
    """Join catalog SKUs with live available quantities from KB-IHMS."""
    try:
        inventory_items = await ihms.get_inventory(headers)
    except GatewayError:
        if not allow_degraded:
            raise
        logger.warning("IHMS inventory unavailable; returning catalog without stock levels")
        return _catalog_without_inventory(catalog)

    inventory_by_product_id = {
        item.product_id: item.available_quantity for item in inventory_items
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
