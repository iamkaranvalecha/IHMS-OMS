import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ChangeEvent } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCatalog, useCheckoutMutations, useSession } from "@/api/hooks";
import type { CatalogProduct, CheckoutSession, ObservabilityIds } from "@/api/types";
import { App } from "./App";

vi.mock("@/api/hooks", () => ({
  useCatalog: vi.fn(),
  useCheckoutMutations: vi.fn(),
  useSession: vi.fn(),
}));

vi.mock("@/components/CatalogGrid", () => ({
  CatalogGrid: ({ onAdd }: { onAdd: (item: CatalogProduct & { quantity: number; maxQuantity: number }) => void }) => (
    <button
      type="button"
      onClick={() =>
        onAdd({
          sku: "WIDGET-001",
          name: "Widget",
          ihmsProductId: "prod-widget-001",
          ecopsItemCode: "WIDGET-001",
          unitPrice: 19.99,
          availableQuantity: 10,
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
    customerName,
    onCheckout,
    onCustomerNameChange,
  }: {
    cart: unknown;
    customerName: string;
    onCheckout: () => void;
    onCustomerNameChange: (value: string) => void;
  }) => (
    <div>
      <input
        aria-label="Customer name"
        value={customerName}
        onChange={(event: ChangeEvent<HTMLInputElement>) =>
          onCustomerNameChange(event.target.value)
        }
      />
      <button type="button" disabled={!cart} onClick={onCheckout}>
        Place hold
      </button>
    </div>
  ),
}));

vi.mock("@/components/CheckoutPanel", () => ({
  CheckoutPanel: ({ onConfirm }: { onConfirm: () => void }) => (
    <button type="button" onClick={onConfirm}>
      Confirm order
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

const heldSession: CheckoutSession = {
  sessionId: "session-1",
  correlationId: "corr-1",
  state: "HELD",
  holdId: "hold-1",
  orderId: null,
  expiresAt: "2026-07-04T16:00:00Z",
  customerName: "Jane Doe",
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
  const startCheckout = {
    mutateAsync: vi.fn(async () => ({ data: heldSession, observability })),
    isPending: false,
  };
  const confirmCheckout = {
    mutateAsync: vi.fn(async () => {
      throw new Error("network lost after confirm");
    }),
    isPending: false,
  };
  const abandonCheckout = {
    mutateAsync: vi.fn(async () => ({ data: heldSession, observability })),
    isPending: false,
  };

  vi.mocked(useCatalog).mockReturnValue({
    data: { data: [catalogProduct], observability },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useCatalog>);
  vi.mocked(useSession).mockImplementation((sessionId) =>
    ({
      data: sessionId ? { data: heldSession, observability } : undefined,
    }) as unknown as ReturnType<typeof useSession>,
  );
  vi.mocked(useCheckoutMutations).mockReturnValue({
    startCheckout,
    confirmCheckout,
    abandonCheckout,
  } as unknown as ReturnType<typeof useCheckoutMutations>);

  return { startCheckout, confirmCheckout };
}

describe("App confirm idempotency", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.sessionStorage.clear();
    vi.clearAllMocks();
    const randomUUID = vi.fn<() => ReturnType<Crypto["randomUUID"]>>();
    randomUUID.mockReturnValue("00000000-0000-4000-8000-000000000001");
    vi.stubGlobal("crypto", { randomUUID });
  });

  it("reuses the checkout idempotency key across failed confirm retries", async () => {
    const { startCheckout, confirmCheckout } = setupHooks();

    render(<App />);

    fireEvent.click(screen.getByText("Add Widget"));
    fireEvent.change(screen.getByLabelText("Customer name"), { target: { value: "Jane Doe" } });
    fireEvent.click(screen.getByText("Place hold"));

    await waitFor(() => expect(startCheckout.mutateAsync).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.queryByText("Confirm order")).not.toBeNull());

    fireEvent.click(screen.getByText("Confirm order"));
    await waitFor(() => expect(confirmCheckout.mutateAsync).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByText("Confirm order"));
    await waitFor(() => expect(confirmCheckout.mutateAsync).toHaveBeenCalledTimes(2));

    expect(confirmCheckout.mutateAsync).toHaveBeenNthCalledWith(1, {
      sessionId: "session-1",
      idempotencyKey: "00000000-0000-4000-8000-000000000001",
    });
    expect(confirmCheckout.mutateAsync).toHaveBeenNthCalledWith(2, {
      sessionId: "session-1",
      idempotencyKey: "00000000-0000-4000-8000-000000000001",
    });
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1);
  });

  it("resumes a stored active checkout with the original idempotency key", async () => {
    const { confirmCheckout } = setupHooks();
    window.sessionStorage.setItem(
      "checkout-orchestrator.active-checkout",
      JSON.stringify({
        sessionId: "session-1",
        confirmIdempotencyKey: "stored-idem-key",
      }),
    );

    render(<App />);

    await waitFor(() => expect(screen.queryByText("Confirm order")).not.toBeNull());
    fireEvent.click(screen.getByText("Confirm order"));

    await waitFor(() => expect(confirmCheckout.mutateAsync).toHaveBeenCalledTimes(1));
    expect(confirmCheckout.mutateAsync).toHaveBeenCalledWith({
      sessionId: "session-1",
      idempotencyKey: "stored-idem-key",
    });
    expect(crypto.randomUUID).not.toHaveBeenCalled();
  });
});
