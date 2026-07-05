import { useState } from "react";

import type { CatalogProduct, CartItem } from "@/api/types";
import { formatCurrency } from "@/api/normalize";

interface CatalogGridProps {
  products: CatalogProduct[];
  cart: CartItem | null;
  onAdd: (item: CartItem) => void;
  disabled?: boolean;
}

const UNKNOWN_STOCK_CAP = 99;

function maxPurchasable(product: CatalogProduct): number {
  if (product.availableQuantity === null) {
    return UNKNOWN_STOCK_CAP;
  }
  return Math.max(product.availableQuantity, 0);
}

export function CatalogGrid({ products, cart, onAdd, disabled }: CatalogGridProps) {
  const [quantities, setQuantities] = useState<Record<string, number>>({});

  return (
    <section className="panel">
      <h2>Inventory</h2>
      <ul className="catalog-grid">
        {products.map((product) => {
          const inCart = cart?.sku === product.sku;
          const stockUnknown = product.availableQuantity === null;
          const outOfStock = !stockUnknown && product.availableQuantity <= 0;
          const maxQty = maxPurchasable(product);
          const selectedQty = quantities[product.sku] ?? 1;
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
                        [product.sku]: Math.min(Math.max(parsed, 1), maxQty),
                      }));
                    }}
                  />
                </label>
              )}
              <button
                type="button"
                disabled={disabled || inCart || outOfStock}
                onClick={() => {
                  const quantity = Math.min(Math.max(selectedQty, 1), maxQty);
                  onAdd({
                    sku: product.sku,
                    name: product.name,
                    unitPrice: product.unitPrice,
                    quantity,
                    maxQuantity: maxQty,
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
