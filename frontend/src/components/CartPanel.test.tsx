import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CartItem } from "@/api/types";
import { CartPanel } from "./CartPanel";

const cart: CartItem[] = [
  {
    sku: "WIDGET-001",
    name: "Widget",
    unitPrice: 19.99,
    quantity: 1,
    maxQuantity: 10,
    stockUnknown: false,
  },
];

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

    fireEvent.change(screen.getByLabelText("Quantity for Widget"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Place order" }));

    expect(onCartChange).toHaveBeenCalledWith([{ ...cart[0], quantity: 5 }]);
    expect(onCheckout).toHaveBeenCalledWith([{ ...cart[0], quantity: 5 }]);
  });

  it("allows checkout with a positive quantity when stock level is unknown", () => {
    const onCartChange = vi.fn();
    const onCheckout = vi.fn();
    const unknownStockCart: CartItem[] = [
      {
        ...cart[0],
        maxQuantity: 1,
        stockUnknown: true,
      },
    ];

    render(
      <CartPanel
        cart={unknownStockCart}
        customerName="Jane Doe"
        onCustomerNameChange={vi.fn()}
        onCartChange={onCartChange}
        onRemove={vi.fn()}
        onCheckout={onCheckout}
        checkoutPending={false}
      />,
    );

    fireEvent.change(screen.getByLabelText("Quantity for Widget"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Place order" }));

    expect(onCartChange).toHaveBeenCalledWith([{ ...unknownStockCart[0], quantity: 4, maxQuantity: 4 }]);
    expect(onCheckout).toHaveBeenCalledWith([{ ...unknownStockCart[0], quantity: 4, maxQuantity: 4 }]);
  });

  it("blocks checkout when quantity exceeds available stock", () => {
    const onCheckout = vi.fn();

    render(
      <CartPanel
        cart={[{ ...cart[0], quantity: 12, maxQuantity: 10 }]}
        customerName="Jane Doe"
        onCustomerNameChange={vi.fn()}
        onCartChange={vi.fn()}
        onRemove={vi.fn()}
        onCheckout={onCheckout}
        checkoutPending={false}
      />,
    );

    expect(screen.getByRole("button", { name: "Place order" })).toHaveProperty("disabled", true);
    expect(screen.getByRole("alert").textContent).toMatch(/only 10 available/);
    fireEvent.click(screen.getByRole("button", { name: "Place order" }));
    expect(onCheckout).not.toHaveBeenCalled();
  });

  it("preserves in-progress quantity input when unrelated cart lines change", () => {
    const onCartChange = vi.fn();

    const { rerender } = render(
      <CartPanel
        cart={cart}
        customerName="Jane Doe"
        onCustomerNameChange={vi.fn()}
        onCartChange={onCartChange}
        onRemove={vi.fn()}
        onCheckout={vi.fn()}
        checkoutPending={false}
      />,
    );

    fireEvent.change(screen.getByLabelText("Quantity for Widget"), { target: { value: "5" } });

    rerender(
      <CartPanel
        cart={[
          cart[0],
          {
            sku: "GADGET-002",
            name: "Gadget",
            unitPrice: 49.99,
            quantity: 1,
            maxQuantity: 5,
            stockUnknown: false,
          },
        ]}
        customerName="Jane Doe"
        onCustomerNameChange={vi.fn()}
        onCartChange={onCartChange}
        onRemove={vi.fn()}
        onCheckout={vi.fn()}
        checkoutPending={false}
      />,
    );

    expect((screen.getByLabelText("Quantity for Widget") as HTMLInputElement).value).toBe("5");
  });
});
