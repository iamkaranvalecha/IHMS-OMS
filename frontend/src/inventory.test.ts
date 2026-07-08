import { describe, expect, it } from "vitest";

import type { CartItem } from "@/api/types";
import {
  checkoutBlockReason,
  isCartOverAvailableStock,
  quantityOnHoldInCart,
} from "@/inventory";

const widget: CartItem = {
  sku: "WIDGET-001",
  name: "Widget",
  unitPrice: 19.99,
  quantity: 6,
  maxQuantity: 5,
  stockUnknown: false,
};

describe("inventory helpers", () => {
  it("sums on-hold quantity from cart for a sku", () => {
    expect(quantityOnHoldInCart([widget], "WIDGET-001")).toBe(6);
    expect(quantityOnHoldInCart([widget], "GADGET-002")).toBe(0);
  });

  it("detects cart lines over available stock", () => {
    expect(isCartOverAvailableStock([widget])).toBe(true);
    expect(isCartOverAvailableStock([{ ...widget, quantity: 5 }])).toBe(false);
  });

  it("returns a checkout block reason when quantity exceeds available", () => {
    expect(checkoutBlockReason([widget])).toMatch(/only 5 available/);
    expect(checkoutBlockReason([widget], { "WIDGET-001": "6" })).toMatch(/only 5 available/);
  });
});
