import { useEffect, useState } from "react";

import {
  cartSubtotal,
  clampLineQuantity,
  resolveDisplayLines,
  updateCartLine,
} from "@/cart";
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
  const [dirtySkus, setDirtySkus] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setQuantityInputs((current) => {
      const next = { ...current };
      for (const line of cart) {
        if (dirtySkus.has(line.sku)) {
          continue;
        }
        next[line.sku] = String(line.quantity);
      }
      for (const sku of Object.keys(next)) {
        if (!cart.some((line) => line.sku === sku)) {
          delete next[sku];
        }
      }
      return next;
    });
  }, [cart, dirtySkus]);

  if (cart.length === 0) {
    return (
      <section className="panel">
        <h2>Cart</h2>
        <p className="muted">Add a product to start checkout.</p>
      </section>
    );
  }

  const displayLines = resolveDisplayLines(cart, quantityInputs);

  const commitLineQuantity = (line: CartItem): CartItem => {
    const parsed = Number.parseInt(quantityInputs[line.sku] ?? String(line.quantity), 10);
    const quantity = Number.isFinite(parsed)
      ? clampLineQuantity(line, parsed)
      : line.quantity;
    const nextLine = updateCartLine([line], line.sku, quantity)[0];
    setQuantityInputs((current) => ({ ...current, [line.sku]: String(quantity) }));
    setDirtySkus((current) => {
      const next = new Set(current);
      next.delete(line.sku);
      return next;
    });
    if (quantity !== line.quantity || nextLine.maxQuantity !== line.maxQuantity) {
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
        ? clampLineQuantity(line, parsed)
        : line.quantity;
      const nextLine = updateCartLine([line], line.sku, quantity)[0];
      committed.push(nextLine);
      if (quantity !== line.quantity || nextLine.maxQuantity !== line.maxQuantity) {
        nextCart = updateCartLine(nextCart, line.sku, quantity);
      }
      setQuantityInputs((current) => ({ ...current, [line.sku]: String(quantity) }));
    }
    setDirtySkus(new Set());
    if (nextCart !== cart) {
      onCartChange(nextCart);
    }
    return committed;
  };

  return (
    <section className="panel">
      <h2>Cart</h2>
      <ul className="cart-lines">
        {displayLines.map((line) => (
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
                max={line.stockUnknown ? undefined : line.maxQuantity}
                value={quantityInputs[line.sku] ?? String(line.quantity)}
                disabled={disabled}
                aria-label={`Quantity for ${line.name}`}
                onChange={(event) => {
                  setDirtySkus((current) => new Set(current).add(line.sku));
                  setQuantityInputs((current) => ({
                    ...current,
                    [line.sku]: event.target.value,
                  }));
                }}
                onBlur={() => {
                  commitLineQuantity(cart.find((entry) => entry.sku === line.sku) ?? line);
                }}
              />
            </label>
            <p className="muted">
              {line.stockUnknown
                ? "Stock level unknown — hold may fail if insufficient"
                : line.maxQuantity === 0
                  ? "Out of stock"
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
        Subtotal: <strong>{formatCurrency(cartSubtotal(displayLines))}</strong>
      </p>
      <label className="field">
        <span>Name (optional)</span>
        <input
          type="text"
          value={customerName}
          onChange={(e) => onCustomerNameChange(e.target.value)}
          disabled={disabled}
          placeholder="Guest"
        />
      </label>
      <button
        type="button"
        className="primary"
        disabled={
          disabled ||
          checkoutPending ||
          displayLines.length === 0 ||
          displayLines.some((line) => !line.stockUnknown && line.maxQuantity === 0)
        }
        onClick={() => {
          onCheckout(commitAllLines());
        }}
      >
        {checkoutPending ? "Placing order…" : "Place order"}
      </button>
    </section>
  );
}
