import type { CartItem } from "@/api/types";

/** Quantities in the cart (pending checkout) — mirrors KB-IHMS "on hold in this browser". */
export function quantityOnHoldInCart(cart: CartItem[], sku: string): number {
  return cart.find((line) => line.sku === sku)?.quantity ?? 0;
}

/** True when a line requests more than IHMS reports as available. */
export function isLineOverAvailableStock(line: CartItem): boolean {
  return !line.stockUnknown && line.quantity > line.maxQuantity;
}

/** Block checkout when any line exceeds live available stock. */
export function isCartOverAvailableStock(cart: CartItem[]): boolean {
  return cart.some(isLineOverAvailableStock);
}

function effectiveCartLines(
  cart: CartItem[],
  quantityInputs?: Record<string, string>,
): CartItem[] {
  if (!quantityInputs) {
    return cart;
  }
  return cart.map((line) => {
    const raw = quantityInputs[line.sku];
    if (raw === undefined) {
      return line;
    }
    const parsed = Number.parseInt(raw, 10);
    if (!Number.isFinite(parsed)) {
      return line;
    }
    return { ...line, quantity: parsed };
  });
}

export function checkoutBlockReason(
  cart: CartItem[],
  quantityInputs?: Record<string, string>,
): string | null {
  const lines = effectiveCartLines(cart, quantityInputs);
  const over = lines.find(isLineOverAvailableStock);
  if (over) {
    return `${over.name}: requested ${over.quantity}, only ${over.maxQuantity} available`;
  }
  const outOfStock = lines.find((line) => !line.stockUnknown && line.maxQuantity === 0);
  if (outOfStock) {
    return `${outOfStock.name} is out of stock`;
  }
  return null;
}
