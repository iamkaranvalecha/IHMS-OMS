import type { CatalogProduct, CartItem } from "@/api/types";
import { formatCurrency } from "@/api/normalize";

interface CatalogGridProps {
  products: CatalogProduct[];
  cart: CartItem | null;
  onAdd: (item: CartItem) => void;
  disabled?: boolean;
}

export function CatalogGrid({ products, cart, onAdd, disabled }: CatalogGridProps) {
  return (
    <section className="panel">
      <h2>Inventory</h2>
      <ul className="catalog-grid">
        {products.map((product) => {
          const inCart = cart?.sku === product.sku;
          const outOfStock = product.availableQuantity <= 0;
          const maxQty = Math.max(product.availableQuantity, 0);
          return (
            <li key={product.sku} className="catalog-card">
              <h3>{product.name}</h3>
              <p className="sku">{product.sku}</p>
              <p className="price">{formatCurrency(product.unitPrice)}</p>
              <p className={outOfStock ? "stock stock-out" : "stock"}>
                {outOfStock ? "Out of stock" : `${product.availableQuantity} in stock`}
              </p>
              {!outOfStock && (
                <label className="field quantity-field">
                  <span>Quantity</span>
                  <input
                    type="number"
                    min={1}
                    max={maxQty}
                    defaultValue={1}
                    disabled={disabled || inCart}
                    id={`qty-${product.sku}`}
                  />
                </label>
              )}
              <button
                type="button"
                disabled={disabled || inCart || outOfStock}
                onClick={() => {
                  const input = document.getElementById(`qty-${product.sku}`) as HTMLInputElement;
                  const parsed = Number.parseInt(input?.value ?? "1", 10);
                  const quantity = Number.isFinite(parsed)
                    ? Math.min(Math.max(parsed, 1), maxQty)
                    : 1;
                  onAdd({
                    sku: product.sku,
                    name: product.name,
                    unitPrice: product.unitPrice,
                    quantity,
                    maxQuantity: maxQty,
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
