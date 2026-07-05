import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CatalogProduct } from "@/api/types";
import { CatalogGrid } from "./CatalogGrid";

const productWithUnknownStock: CatalogProduct = {
  sku: "WIDGET-001",
  name: "Widget",
  ihmsProductId: "prod-widget-001",
  ecopsItemCode: "WIDGET-001",
  unitPrice: 19.99,
  availableQuantity: null,
};

describe("CatalogGrid", () => {
  afterEach(() => {
    cleanup();
  });

  it("allows adding products when inventory quantity is temporarily unknown", () => {
    const onAdd = vi.fn();

    render(
      <CatalogGrid
        products={[productWithUnknownStock]}
        cart={null}
        onAdd={onAdd}
      />,
    );

    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Add to cart" }));

    expect(onAdd).toHaveBeenCalledWith({
      sku: "WIDGET-001",
      name: "Widget",
      unitPrice: 19.99,
      quantity: 3,
      maxQuantity: 3,
      stockUnknown: true,
    });
  });
});
