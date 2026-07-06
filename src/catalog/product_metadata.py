"""Static product metadata keyed by IHMS productId (prices, SKUs — not in IHMS inventory API)."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProductMetadata:
    sku: str
    unit_price: float
    description: str = ""
    category: str = ""


class ProductMetadataCatalog:
    """Orchestrator-owned pricing and SKU mapping for IHMS inventory rows."""

    def __init__(self, products: dict[str, ProductMetadata]) -> None:
        self._products = products

    @classmethod
    def from_path(cls, path: Path) -> "ProductMetadataCatalog":
        if not path.exists():
            return cls({})
        raw = json.loads(path.read_text(encoding="utf-8"))
        products_raw = raw.get("products", {})
        if not isinstance(products_raw, dict):
            return cls({})
        products: dict[str, ProductMetadata] = {}
        for product_id, entry in products_raw.items():
            if not isinstance(entry, dict):
                continue
            sku = str(entry.get("sku") or product_id)
            products[str(product_id)] = ProductMetadata(
                sku=sku,
                unit_price=float(entry.get("unit_price", 0)),
                description=str(entry.get("description", "")),
                category=str(entry.get("category", "")),
            )
        return cls(products)

    def get(self, product_id: str) -> ProductMetadata | None:
        return self._products.get(product_id)

    def metadata_or_default(self, product_id: str, name: str) -> ProductMetadata:
        meta = self._products.get(product_id)
        if meta is not None:
            return meta
        return ProductMetadata(
            sku=product_id,
            unit_price=0.0,
            description=name,
        )
