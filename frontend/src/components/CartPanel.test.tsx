import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CartItem } from "@/api/types";
import { CartPanel } from "./CartPanel";

const cart: CartItem = {
  sku: "WIDGET-001",
  name: "Widget",
  unitPrice: 19.99,
  quantity: 1,
  maxQuantity: 10,
  stockUnknown: false,
};

describe("CartPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("uses the typed quantity when checkout is clicked before blur commits it", () => {
    const onCartChange = vi.fn();
    const onCheckout = vi.fn();

    render(
      <CartPanel
        cart={cart}
        customerName="Jane Doe"
        onCustomerNameChange={vi.fn()}
        onCartChange={onCartChange}
        onRemove={vi.fn()}
        onCheckout={onCheckout}
        checkoutPending={false}
      />,
    );

    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Place hold & checkout" }));

    expect(onCartChange).toHaveBeenCalledWith({ ...cart, quantity: 5 });
    expect(onCheckout).toHaveBeenCalledWith({ ...cart, quantity: 5 });
  });
});
