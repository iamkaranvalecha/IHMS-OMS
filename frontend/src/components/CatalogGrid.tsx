import { useState } from "react";

import type { CatalogProduct, CartItem } from "@/api/types";
import { formatCurrency } from "@/api/normalize";
import { quantityOnHoldInCart } from "@/inventory";

interface CatalogGridProps {
  products: CatalogProduct[];
  cart: CartItem[];
  onAdd: (item: CartItem) => void;
  disabled?: boolean;
}

export function CatalogGrid({ products, cart, onAdd, disabled }: CatalogGridProps) {
  const [quantities, setQuantities] = useState<Record<string, number>>({});

  return (
    <section className="panel">
      <h2>Inventory</h2>
      <table className="inventory-table">
        <thead>
          <tr>
            <th>Product</th>
            <th>Name</th>
            <th>Price</th>
            <th>Available</th>
            <th>On hold</th>
            <th>Add</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const inCart = cart.some((line) => line.sku === product.sku);
            const availableQuantity = product.availableQuantity;
            const stockUnknown = availableQuantity === null;
            const onHold = quantityOnHoldInCart(cart, product.sku);
            const outOfStock = availableQuantity !== null && availableQuantity <= 0;
            const maxQty =
              availableQuantity === null ? undefined : Math.max(availableQuantity, 0);
            const selectedQty = quantities[product.sku] ?? 1;
            const clampQuantity = (value: number): number => {
              const positive = Math.max(value, 1);
              return maxQty === undefined ? positive : Math.min(positive, maxQty);
            };
            return (
              <tr key={product.sku}>
                <td>
                  <span className="sku">{product.sku}</span>
                </td>
                <td>
                  <span className="inventory-name">{product.name}</span>
                  {product.description ? (
                    <span className="muted inventory-description">{product.description}</span>
                  ) : null}
                </td>
                <td>{formatCurrency(product.unitPrice)}</td>
                <td>
                  {stockUnknown ? "…" : outOfStock ? <span className="stock-out">0</span> : availableQuantity}
                </td>
                <td>{onHold}</td>
                <td className="inventory-actions">
                  {!outOfStock && (
                    <label className="field quantity-field">
                      <span className="sr-only">Quantity for {product.name}</span>
                      <input
                        type="number"
                        min={1}
                        max={maxQty}
                        value={selectedQty}
                        disabled={disabled}
                        aria-label={`Quantity for ${product.name}`}
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
                    disabled={disabled || outOfStock}
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
                    {inCart ? "Add more" : outOfStock ? "Unavailable" : "Add to cart"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="muted">
        Available is live stock from IHMS after all holds. On hold is the quantity in your cart
        (pending checkout).
      </p>
    </section>
  );
}
