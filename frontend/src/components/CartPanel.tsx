import { useEffect, useState } from "react";

import type { CartItem } from "@/api/types";
import { formatCurrency } from "@/api/normalize";

interface CartPanelProps {
  cart: CartItem | null;
  customerName: string;
  onCustomerNameChange: (value: string) => void;
  onCartChange: (item: CartItem | null) => void;
  onRemove: () => void;
  onCheckout: (item: CartItem) => void;
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
  const [quantityInput, setQuantityInput] = useState(cart ? String(cart.quantity) : "1");

  useEffect(() => {
    if (cart) {
      setQuantityInput(String(cart.quantity));
    }
  }, [cart?.sku, cart?.quantity]);

  if (!cart) {
    return (
      <section className="panel">
        <h2>Cart</h2>
        <p className="muted">Add a product to start checkout.</p>
      </section>
    );
  }

  const commitQuantity = (): CartItem => {
    const parsed = Number.parseInt(quantityInput, 10);
    const quantity = Number.isFinite(parsed)
      ? Math.min(Math.max(parsed, 1), cart.maxQuantity)
      : cart.quantity;
    const nextCart = quantity !== cart.quantity ? { ...cart, quantity } : cart;
    setQuantityInput(String(quantity));
    if (quantity !== cart.quantity) {
      onCartChange(nextCart);
    }
    return nextCart;
  };

  return (
    <section className="panel">
      <h2>Cart</h2>
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
          value={quantityInput}
          disabled={disabled}
          onChange={(event) => setQuantityInput(event.target.value)}
          onBlur={commitQuantity}
        />
      </label>
      <p className="muted">
        {cart.stockUnknown
          ? "Stock level unknown — hold may fail if insufficient"
          : `Up to ${cart.maxQuantity} available`}
      </p>
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
        disabled={disabled || checkoutPending || !customerName.trim() || cart.stockUnknown}
        onClick={() => {
          const nextCart = commitQuantity();
          onCheckout(nextCart);
        }}
      >
        {checkoutPending ? "Placing hold…" : "Place hold & checkout"}
      </button>
    </section>
  );
}
