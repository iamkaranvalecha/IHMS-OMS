"""CatalogProvider protocol and JSON file implementation."""

import json
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class CatalogProduct(BaseModel):
    """Orchestrator-facing product view."""

    sku: str
    name: str
    ihms_product_id: str = Field(description="KB-IHMS product identifier")
    ecops_item_code: str = Field(description="EC-OPS order line item code")
    unit_price: float


class CatalogProvider(Protocol):
    """Anti-corruption layer between orchestrator and upstream product identifiers."""

    def get_product(self, sku: str) -> CatalogProduct | None: ...

    def list_products(self) -> list[CatalogProduct]: ...


class JsonCatalogProvider:
    """Load catalog mapping from a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._products: dict[str, CatalogProduct] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for entry in raw.get("products", []):
            product = CatalogProduct.model_validate(entry)
            self._products[product.sku] = product

    def get_product(self, sku: str) -> CatalogProduct | None:
        return self._products.get(sku)

    def list_products(self) -> list[CatalogProduct]:
        return list(self._products.values())
