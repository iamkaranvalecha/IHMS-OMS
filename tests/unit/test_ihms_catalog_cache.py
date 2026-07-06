"""Unit tests for IHMS catalog cache and EC-OPS mapping."""

import httpx
import pytest
import respx
from src.catalog.ecops_mapping import EcopsMapping
from src.catalog.ihms_cache import IhmsCatalogCache
from src.gateway.headers import ObservabilityHeaders
from src.gateway.ihms_client import IhmsClient

OBS = ObservabilityHeaders(
    request_id="req-1",
    correlation_id="corr-1",
    trace_id="trace-1",
)


def test_ecops_mapping_defaults_to_sku() -> None:
    mapping = EcopsMapping({"MOUSE-001": "MOUSE-CUSTOM"})
    assert mapping.ecops_item_code("MOUSE-001") == "MOUSE-CUSTOM"
    assert mapping.ecops_item_code("KEYBOARD-002") == "KEYBOARD-002"


@respx.mock
@pytest.mark.asyncio
async def test_ihms_catalog_cache_refresh_maps_products() -> None:
    respx.get("http://ihms.test/api/products").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "productId": "prod-001",
                    "sku": "MOUSE-001",
                    "name": "Wireless Mouse",
                    "unitPrice": 29.99,
                    "availableQuantity": 5,
                    "sellable": True,
                }
            ],
        )
    )
    ihms = IhmsClient(httpx.AsyncClient(), "http://ihms.test")
    cache = IhmsCatalogCache()
    await cache.refresh(ihms, EcopsMapping(), OBS)

    products = cache.list()
    assert len(products) == 1
    assert products[0].sku == "MOUSE-001"
    assert products[0].ihms_product_id == "prod-001"
    assert products[0].ecops_item_code == "MOUSE-001"
    assert products[0].available_quantity == 5


def test_ihms_catalog_cache_load_from_json_catalog() -> None:
    from pathlib import Path

    from src.catalog.provider import JsonCatalogProvider

    path = Path(__file__).resolve().parents[2] / "catalog" / "products.json"
    json_catalog = JsonCatalogProvider(path)
    cache = IhmsCatalogCache()
    cache.load_from_json_catalog(json_catalog, EcopsMapping())

    products = cache.list()
    assert len(products) >= 1
    assert products[0].sku == "WIDGET-001"
    assert products[0].available_quantity == 0
