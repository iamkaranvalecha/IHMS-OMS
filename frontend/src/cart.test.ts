import { describe, expect, it } from "vitest";

import type { CartItem } from "@/api/types";
import { addToCart, syncCartWithCatalog } from "@/cart";

const widget: CartItem = {
  sku: "WIDGET-001",
  name: "Widget",
  unitPrice: 19.99,
  quantity: 4,
  maxQuantity: 5,
  stockUnknown: false,
};

describe("addToCart", () => {
  it("respects the lower maxQuantity when merging duplicate skus", () => {
    const staleLine = { ...widget, maxQuantity: 3, quantity: 2 };
    const incoming = { ...widget, maxQuantity: 5, quantity: 2 };

    const result = addToCart([staleLine], incoming);

    expect(result[0].quantity).toBe(3);
  });

  it("allows unknown-stock lines to grow beyond the initial maxQuantity", () => {
    const existing = {
      ...widget,
      quantity: 3,
      maxQuantity: 3,
      stockUnknown: true,
    };

    const result = addToCart([existing], { ...existing, quantity: 2 });

    expect(result[0].quantity).toBe(5);
    expect(result[0].maxQuantity).toBe(5);
  });
});

describe("syncCartWithCatalog", () => {
  it("returns the same cart reference when nothing changed", () => {
    const cart = [widget];
    const products = [{ sku: "WIDGET-001", availableQuantity: 5, unitPrice: 19.99 }];

    expect(syncCartWithCatalog(cart, products)).toBe(cart);
  });

  it("zeros quantity when stock drops to out of stock", () => {
    const cart = [widget];
    const products = [{ sku: "WIDGET-001", availableQuantity: 0, unitPrice: 19.99 }];

    const result = syncCartWithCatalog(cart, products);

    expect(result[0].maxQuantity).toBe(0);
    expect(result[0].quantity).toBe(0);
  });
});
