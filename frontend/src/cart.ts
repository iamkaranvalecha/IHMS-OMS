import type { CartItem } from "@/api/types";

export function addToCart(cart: CartItem[], item: CartItem): CartItem[] {
  const existing = cart.find((line) => line.sku === item.sku);
  if (!existing) {
    return [...cart, item];
  }
  const quantity = Math.min(existing.quantity + item.quantity, item.maxQuantity);
  return cart.map((line) => (line.sku === item.sku ? { ...line, quantity } : line));
}

export function updateCartLine(cart: CartItem[], sku: string, quantity: number): CartItem[] {
  return cart.map((line) => (line.sku === sku ? { ...line, quantity } : line));
}

export function removeFromCart(cart: CartItem[], sku: string): CartItem[] {
  return cart.filter((line) => line.sku !== sku);
}

export function cartSubtotal(cart: CartItem[]): number {
  return cart.reduce((total, line) => total + line.unitPrice * line.quantity, 0);
}

export function cartHasUnknownStock(cart: CartItem[]): boolean {
  return cart.some((line) => line.stockUnknown);
}

export function syncCartWithCatalog(
  cart: CartItem[],
  products: Array<{ sku: string; availableQuantity: number | null; unitPrice: number }>,
): CartItem[] {
  return cart.map((line) => {
    const product = products.find((item) => item.sku === line.sku);
    if (!product) {
      return line;
    }
    const stockUnknown = product.availableQuantity === null;
    const maxQuantity =
      product.availableQuantity === null
        ? line.maxQuantity
        : Math.max(product.availableQuantity, 0);
    const quantity =
      maxQuantity > 0 ? Math.min(line.quantity, maxQuantity) : line.quantity;
    if (
      line.maxQuantity === maxQuantity &&
      line.quantity === quantity &&
      line.stockUnknown === stockUnknown
    ) {
      return line;
    }
    return { ...line, maxQuantity, quantity, stockUnknown };
  });
}
