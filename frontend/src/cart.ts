import type { CartItem } from "@/api/types";

export function clampLineQuantity(line: CartItem, quantity: number): number {
  const positive = Math.max(quantity, 1);
  if (line.stockUnknown) {
    return positive;
  }
  return Math.min(positive, line.maxQuantity);
}

export function addToCart(cart: CartItem[], item: CartItem): CartItem[] {
  const existing = cart.find((line) => line.sku === item.sku);
  if (!existing) {
    return [...cart, item];
  }

  const nextQuantity = existing.quantity + item.quantity;
  if (existing.stockUnknown || item.stockUnknown) {
    const quantity = nextQuantity;
    const maxQuantity = Math.max(existing.maxQuantity, item.maxQuantity, quantity);
    return cart.map((line) =>
      line.sku === item.sku
        ? { ...line, quantity, maxQuantity, stockUnknown: true }
        : line,
    );
  }

  const maxAllowed = Math.min(existing.maxQuantity, item.maxQuantity);
  const quantity = Math.min(nextQuantity, maxAllowed);
  return cart.map((line) => (line.sku === item.sku ? { ...line, quantity } : line));
}

export function updateCartLine(cart: CartItem[], sku: string, quantity: number): CartItem[] {
  return cart.map((line) => {
    if (line.sku !== sku) {
      return line;
    }
    const nextQuantity = clampLineQuantity(line, quantity);
    const maxQuantity = line.stockUnknown
      ? Math.max(line.maxQuantity, nextQuantity)
      : line.maxQuantity;
    return { ...line, quantity: nextQuantity, maxQuantity };
  });
}

export function removeFromCart(cart: CartItem[], sku: string): CartItem[] {
  return cart.filter((line) => line.sku !== sku);
}

export function cartSubtotal(cart: CartItem[]): number {
  return cart.reduce((total, line) => total + line.unitPrice * line.quantity, 0);
}

export function resolveDisplayLines(
  cart: CartItem[],
  quantityInputs: Record<string, string>,
): CartItem[] {
  return cart.map((line) => {
    const raw = quantityInputs[line.sku];
    if (raw === undefined) {
      return line;
    }
    const parsed = Number.parseInt(raw, 10);
    if (!Number.isFinite(parsed)) {
      return line;
    }
    return { ...line, quantity: clampLineQuantity(line, parsed) };
  });
}

export function syncCartWithCatalog(
  cart: CartItem[],
  products: Array<{ sku: string; availableQuantity: number | null; unitPrice: number }>,
): CartItem[] {
  let changed = false;
  const next = cart.map((line) => {
    const product = products.find((item) => item.sku === line.sku);
    if (!product) {
      return line;
    }
    const stockUnknown = product.availableQuantity === null;
    const maxQuantity = stockUnknown
      ? line.maxQuantity
      : Math.max(product.availableQuantity ?? 0, 0);
    const quantity =
      maxQuantity === 0
        ? 0
        : maxQuantity > 0
          ? Math.min(line.quantity, maxQuantity)
          : line.quantity;
    if (
      line.maxQuantity === maxQuantity &&
      line.quantity === quantity &&
      line.stockUnknown === stockUnknown &&
      line.unitPrice === product.unitPrice
    ) {
      return line;
    }
    changed = true;
    return { ...line, maxQuantity, quantity, stockUnknown, unitPrice: product.unitPrice };
  });
  return changed ? next : cart;
}
