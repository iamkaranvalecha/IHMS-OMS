import { useEffect, useState } from "react";

import { cartHasUnknownStock, cartSubtotal, updateCartLine } from "@/cart";
import type { CartItem } from "@/api/types";
import { formatCurrency } from "@/api/normalize";

interface CartPanelProps {
  cart: CartItem[];
  customerName: string;
  onCustomerNameChange: (value: string) => void;
  onCartChange: (cart: CartItem[]) => void;
  onRemove: (sku: string) => void;
  onCheckout: (cart: CartItem[]) => void;
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
  const [quantityInputs, setQuantityInputs] = useState<Record<string, string>>({});

  useEffect(() => {
    setQuantityInputs((current) => {
      const next = { ...current };
      for (const line of cart) {
        next[line.sku] = String(line.quantity);
      }
      return next;
    });
  }, [cart]);

  if (cart.length === 0) {
    return (
      <section className="panel">
        <h2>Cart</h2>
        <p className="muted">Add a product to start checkout.</p>
      </section>
    );
  }

  const commitLineQuantity = (line: CartItem): CartItem => {
    const parsed = Number.parseInt(quantityInputs[line.sku] ?? String(line.quantity), 10);
    const quantity = Number.isFinite(parsed)
      ? Math.min(Math.max(parsed, 1), line.maxQuantity)
      : line.quantity;
    const nextLine = quantity !== line.quantity ? { ...line, quantity } : line;
    setQuantityInputs((current) => ({ ...current, [line.sku]: String(quantity) }));
    if (quantity !== line.quantity) {
      onCartChange(updateCartLine(cart, line.sku, quantity));
    }
    return nextLine;
  };

  const commitAllLines = (): CartItem[] => {
    let nextCart = cart;
    const committed: CartItem[] = [];
    for (const line of cart) {
      const parsed = Number.parseInt(quantityInputs[line.sku] ?? String(line.quantity), 10);
      const quantity = Number.isFinite(parsed)
        ? Math.min(Math.max(parsed, 1), line.maxQuantity)
        : line.quantity;
      const nextLine = { ...line, quantity };
      committed.push(nextLine);
      if (quantity !== line.quantity) {
        nextCart = updateCartLine(nextCart, line.sku, quantity);
      }
      setQuantityInputs((current) => ({ ...current, [line.sku]: String(quantity) }));
    }
    if (nextCart !== cart) {
      onCartChange(nextCart);
    }
    return committed;
  };

  const stockUnknown = cartHasUnknownStock(cart);

  return (
    <section className="panel">
      <h2>Cart</h2>
      <ul className="cart-lines">
        {cart.map((line) => (
          <li key={line.sku} className="cart-line">
            <div className="cart-line-header">
              <span>
                {line.name} × {line.quantity}
              </span>
              <span>{formatCurrency(line.unitPrice * line.quantity)}</span>
            </div>
            <label className="field quantity-field">
              <span>Quantity</span>
              <input
                type="number"
                min={1}
                max={line.maxQuantity}
                value={quantityInputs[line.sku] ?? String(line.quantity)}
                disabled={disabled}
                aria-label={`Quantity for ${line.name}`}
                onChange={(event) =>
                  setQuantityInputs((current) => ({
                    ...current,
                    [line.sku]: event.target.value,
                  }))
                }
                onBlur={() => {
                  commitLineQuantity(line);
                }}
              />
            </label>
            <p className="muted">
              {line.stockUnknown
                ? "Stock level unknown — hold may fail if insufficient"
                : `Up to ${line.maxQuantity} available`}
            </p>
            <button
              type="button"
              className="link-button"
              onClick={() => onRemove(line.sku)}
              disabled={disabled}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <p className="cart-subtotal">
        Subtotal: <strong>{formatCurrency(cartSubtotal(cart))}</strong>
      </p>
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
        disabled={disabled || checkoutPending || !customerName.trim() || stockUnknown}
        onClick={() => {
          onCheckout(commitAllLines());
        }}
      >
        {checkoutPending ? "Placing hold…" : "Place hold & checkout"}
      </button>
    </section>
  );
}
