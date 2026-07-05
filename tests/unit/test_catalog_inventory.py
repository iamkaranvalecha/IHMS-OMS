"""Unit tests for catalog + IHMS inventory enrichment."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.catalog.inventory import list_catalog_with_inventory
from src.catalog.provider import JsonCatalogProvider
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_models import InventoryItemResponse

OBS = ObservabilityHeaders(request_id="r1", correlation_id="c1", trace_id="t1")


@pytest.fixture
def catalog(tmp_path) -> JsonCatalogProvider:
    path = tmp_path / "products.json"
    path.write_text(
        """
        {
          "products": [
            {
              "sku": "WIDGET-001",
              "name": "Widget",
              "ihms_product_id": "prod-widget-001",
              "ecops_item_code": "WIDGET-001",
              "unit_price": 19.99
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    return JsonCatalogProvider(path)


@pytest.mark.asyncio
async def test_list_catalog_with_inventory_merges_stock(catalog: JsonCatalogProvider) -> None:
    ihms = MagicMock()
    ihms.get_inventory = AsyncMock(
        return_value=[
            InventoryItemResponse(product_id="prod-widget-001", available_quantity=7),
        ]
    )

    products = await list_catalog_with_inventory(catalog, ihms, OBS)

    assert len(products) == 1
    assert products[0].sku == "WIDGET-001"
    assert products[0].available_quantity == 7
    ihms.get_inventory.assert_awaited_once_with(OBS)


@pytest.mark.asyncio
async def test_list_catalog_with_inventory_defaults_missing_products_to_zero(
    catalog: JsonCatalogProvider,
) -> None:
    ihms = MagicMock()
    ihms.get_inventory = AsyncMock(return_value=[])

    products = await list_catalog_with_inventory(catalog, ihms, OBS)

    assert products[0].available_quantity == 0
