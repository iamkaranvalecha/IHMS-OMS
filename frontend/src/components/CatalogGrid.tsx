import { useState } from "react";

import type { CatalogProduct, CartItem } from "@/api/types";
import { formatCurrency } from "@/api/normalize";

interface CatalogGridProps {
  products: CatalogProduct[];
  cart: CartItem | null;
  onAdd: (item: CartItem) => void;
  disabled?: boolean;
}

export function CatalogGrid({ products, cart, onAdd, disabled }: CatalogGridProps) {
  const [quantities, setQuantities] = useState<Record<string, number>>({});

  return (
    <section className="panel">
      <h2>Inventory</h2>
      <ul className="catalog-grid">
        {products.map((product) => {
          const inCart = cart?.sku === product.sku;
          const availableQuantity = product.availableQuantity;
          const stockUnknown = availableQuantity === null;
          const outOfStock = availableQuantity !== null && availableQuantity <= 0;
          const maxQty = availableQuantity === null ? undefined : Math.max(availableQuantity, 0);
          const selectedQty = quantities[product.sku] ?? 1;
          const clampQuantity = (value: number): number => {
            const positive = Math.max(value, 1);
            return maxQty === undefined ? positive : Math.min(positive, maxQty);
          };
          return (
            <li key={product.sku} className="catalog-card">
              <h3>{product.name}</h3>
              <p className="sku">{product.sku}</p>
              <p className="price">{formatCurrency(product.unitPrice)}</p>
              <p className={outOfStock ? "stock stock-out" : "stock"}>
                {stockUnknown
                  ? "Stock unavailable"
                  : outOfStock
                    ? "Out of stock"
                    : `${product.availableQuantity} in stock`}
              </p>
              {!outOfStock && (
                <label className="field quantity-field">
                  <span>Quantity</span>
                  <input
                    type="number"
                    min={1}
                    max={maxQty}
                    value={selectedQty}
                    disabled={disabled || inCart}
                    onChange={(event) => {
                      const parsed = Number.parseInt(event.target.value, 10);
                      if (!Number.isFinite(parsed)) {
                        return;
                      }
                      setQuantities((prev) => ({
                        ...prev,
                        [product.sku]: clampQuantity(parsed),
                      }));
                    }}
                  />
                </label>
              )}
              <button
                type="button"
                disabled={disabled || inCart || outOfStock}
                onClick={() => {
                  const quantity = clampQuantity(selectedQty);
                  onAdd({
                    sku: product.sku,
                    name: product.name,
                    unitPrice: product.unitPrice,
                    quantity,
                    maxQuantity: maxQty ?? quantity,
                    stockUnknown,
                  });
                }}
              >
                {inCart ? "In cart" : outOfStock ? "Unavailable" : "Add to cart"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
