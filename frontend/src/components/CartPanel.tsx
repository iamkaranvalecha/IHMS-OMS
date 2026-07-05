import type { CartItem } from "@/api/types";
import { formatCurrency } from "@/api/normalize";

interface CartPanelProps {
  cart: CartItem | null;
  customerName: string;
  onCustomerNameChange: (value: string) => void;
  onCartChange: (item: CartItem | null) => void;
  onRemove: () => void;
  onCheckout: () => void;
  checkoutPending: boolean;
  disabled?: boolean;
}

export function CartPanel({
  cart,
  customerName,
  onCustomerNameChange,
  onCartChange,
  onRemove,
  onCheckout,
  checkoutPending,
  disabled,
}: CartPanelProps) {
  return (
    <section className="panel">
      <h2>Cart</h2>
      {!cart ? (
        <p className="muted">Add a product to start checkout.</p>
      ) : (
        <>
          <div className="cart-line">
            <span>
              {cart.name} × {cart.quantity}
            </span>
            <span>{formatCurrency(cart.unitPrice * cart.quantity)}</span>
          </div>
          <label className="field quantity-field">
            <span>Quantity</span>
            <input
              type="number"
              min={1}
              max={cart.maxQuantity}
              value={cart.quantity}
              disabled={disabled}
              onChange={(event) => {
                const parsed = Number.parseInt(event.target.value, 10);
                if (!Number.isFinite(parsed)) {
                  return;
                }
                const quantity = Math.min(Math.max(parsed, 1), cart.maxQuantity);
                onCartChange({ ...cart, quantity });
              }}
            />
          </label>
          <p className="muted">Up to {cart.maxQuantity} available</p>
          <button type="button" className="link-button" onClick={onRemove} disabled={disabled}>
            Remove
          </button>
          <label className="field">
            <span>Customer name</span>
            <input
              type="text"
              value={customerName}
              onChange={(e) => onCustomerNameChange(e.target.value)}
              disabled={disabled}
              placeholder="Jane Doe"
            />
          </label>
          <button
            type="button"
            className="primary"
            disabled={disabled || checkoutPending || !customerName.trim()}
            onClick={onCheckout}
          >
            {checkoutPending ? "Placing hold…" : "Place hold & checkout"}
          </button>
        </>
      )}
    </section>
  );
}
