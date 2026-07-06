"""Map IHMS catalog SKUs to EC-OPS order line identifiers."""

import json
from pathlib import Path


class EcopsMapping:
    """Resolve EC-OPS product_name from orchestrator SKU.

    Defaults to using the IHMS SKU when no override is configured.
    """

    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        self._overrides = overrides or {}

    @classmethod
    def from_path(cls, path: Path) -> "EcopsMapping":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        overrides = raw.get("overrides", {})
        if not isinstance(overrides, dict):
            return cls()
        return cls({str(sku): str(code) for sku, code in overrides.items()})

    def ecops_item_code(self, sku: str) -> str:
        return self._overrides.get(sku, sku)
