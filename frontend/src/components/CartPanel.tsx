import type { CartItem } from "@/api/types";
import { formatCurrency } from "@/api/normalize";

interface CartPanelProps {
  cart: CartItem | null;
  customerName: string;
  onCustomerNameChange: (value: string) => void;
  onRemove: () => void;
  onCheckout: () => void;
  checkoutPending: boolean;
  disabled?: boolean;
}

export function CartPanel({
  cart,
  customerName,
  onCustomerNameChange,
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
