import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCatalog, useCheckoutMutations, useSession } from "@/api/hooks";
import type { CartItem, CatalogProduct, CheckoutSession, ObservabilityIds } from "@/api/types";
import { App } from "./App";

vi.mock("@/api/hooks", () => ({
  useCatalog: vi.fn(),
  useCheckoutMutations: vi.fn(),
  useSession: vi.fn(),
}));

vi.mock("@/components/CatalogGrid", () => ({
  CatalogGrid: ({ onAdd }: { onAdd: (item: CartItem) => void }) => (
    <button
      type="button"
      onClick={() =>
        onAdd({
          sku: "WIDGET-001",
          name: "Widget",
          unitPrice: 19.99,
          quantity: 1,
          maxQuantity: 10,
          stockUnknown: false,
        })
      }
    >
      Add Widget
    </button>
  ),
}));

vi.mock("@/components/CartPanel", () => ({
  CartPanel: ({
    cart,
    onCheckout,
  }: {
    cart: CartItem[];
    onCheckout: (items: CartItem[]) => void;
  }) => (
    <button type="button" disabled={cart.length === 0} onClick={() => onCheckout(cart)}>
      Place order
    </button>
  ),
}));

vi.mock("@/components/DevObservabilityPanel", () => ({
  DevObservabilityPanel: () => null,
}));

const observability: ObservabilityIds = {
  requestId: "request-1",
  correlationId: "corr-1",
  traceId: "trace-1",
};

const confirmedSession: CheckoutSession = {
  sessionId: "session-1",
  correlationId: "corr-1",
  state: "CONFIRMED",
  holdId: "hold-1",
  orderId: "order-1",
  expiresAt: null,
  customerName: "Guest",
  lineItems: [{ sku: "WIDGET-001", name: "Widget", quantity: 1, unitPrice: 19.99 }],
};

const catalogProduct: CatalogProduct = {
  sku: "WIDGET-001",
  name: "Widget",
  ihmsProductId: "prod-widget-001",
  ecopsItemCode: "WIDGET-001",
  unitPrice: 19.99,
  availableQuantity: 100,
};

function setupHooks() {
  const placeOrder = {
    mutateAsync: vi.fn(async () => ({ data: confirmedSession, observability })),
    isPending: false,
  };

  vi.mocked(useCatalog).mockReturnValue({
    data: { data: [catalogProduct], observability },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useCatalog>);
  vi.mocked(useSession).mockImplementation((sessionId) =>
    ({
      data: sessionId ? { data: confirmedSession, observability } : undefined,
    }) as unknown as ReturnType<typeof useSession>,
  );
  vi.mocked(useCheckoutMutations).mockReturnValue({
    placeOrder,
  } as unknown as ReturnType<typeof useCheckoutMutations>);

  return { placeOrder };
}

describe("App one-click checkout", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.sessionStorage.clear();
    vi.clearAllMocks();
    vi.stubGlobal("crypto", {
      randomUUID: vi.fn(() => "00000000-0000-4000-8000-000000000001"),
    });
  });

  it("places order with a stable idempotency key on retry", async () => {
    const { placeOrder } = setupHooks();
    placeOrder.mutateAsync
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce({ data: confirmedSession, observability });

    render(<App />);
    fireEvent.click(screen.getByText("Add Widget"));
    fireEvent.click(screen.getByText("Place order"));
    await waitFor(() => expect(placeOrder.mutateAsync).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByText("Place order"));
    await waitFor(() => expect(placeOrder.mutateAsync).toHaveBeenCalledTimes(2));

    expect(placeOrder.mutateAsync).toHaveBeenNthCalledWith(1, {
      cart: expect.any(Array),
      customerName: undefined,
      idempotencyKey: "00000000-0000-4000-8000-000000000001",
      sessionId: undefined,
    });
    expect(placeOrder.mutateAsync).toHaveBeenNthCalledWith(2, {
      cart: expect.any(Array),
      customerName: undefined,
      idempotencyKey: "00000000-0000-4000-8000-000000000001",
      sessionId: undefined,
    });
  });
});
