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
          return (
            <li key={product.sku} className="catalog-card">
              <h3>{product.name}</h3>
              <p className="sku">{product.sku}</p>
              <p className="price">{formatCurrency(product.unitPrice)}</p>
              <button
                type="button"
                disabled={disabled || inCart}
                onClick={() =>
                  onAdd({
                    sku: product.sku,
                    name: product.name,
                    unitPrice: product.unitPrice,
                    quantity: 1,
                  })
                }
              >
                {inCart ? "In cart" : "Add to cart"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
