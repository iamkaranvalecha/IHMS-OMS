"""Smoke tests for scaffold."""

from pathlib import Path

from src import __version__
from src.catalog import JsonCatalogProvider


def test_version_is_set() -> None:
    assert __version__ == "0.6.0"


def test_catalog_loads_products() -> None:
    catalog_path = Path(__file__).resolve().parents[2] / "catalog" / "products.json"
    provider = JsonCatalogProvider(catalog_path)
    products = provider.list_products()
    assert len(products) >= 1
    assert provider.get_product(products[0].sku) is not None
