import { useEffect, useMemo, useRef, useState } from "react";

import { useCatalog, useCheckoutMutations, useSession } from "@/api/hooks";
import { formatCurrency } from "@/api/normalize";
import { isApiError } from "@/api/types";
import type { CartItem, ObservabilityIds } from "@/api/types";
import { addToCart, removeFromCart, syncCartWithCatalog } from "@/cart";
import { CartPanel } from "@/components/CartPanel";
import { CatalogGrid } from "@/components/CatalogGrid";
import { DevObservabilityPanel } from "@/components/DevObservabilityPanel";

function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

const CHECKOUT_STORAGE_KEY = "checkout-orchestrator.checkout";

interface StoredCheckout {
  sessionId: string;
  idempotencyKey: string;
}

function readStoredCheckout(): StoredCheckout | null {
  try {
    const raw = window.sessionStorage.getItem(CHECKOUT_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<StoredCheckout>;
    if (parsed.sessionId && parsed.idempotencyKey) {
      return { sessionId: parsed.sessionId, idempotencyKey: parsed.idempotencyKey };
    }
  } catch {
    // ignore
  }
  return null;
}

function writeStoredCheckout(sessionId: string, idempotencyKey: string): void {
  try {
    window.sessionStorage.setItem(
      CHECKOUT_STORAGE_KEY,
      JSON.stringify({ sessionId, idempotencyKey }),
    );
  } catch {
    // ignore
  }
}

function clearStoredCheckout(): void {
  try {
    window.sessionStorage.removeItem(CHECKOUT_STORAGE_KEY);
  } catch {
    // ignore
  }
}

function isOrderComplete(state: string): boolean {
  return ["CONFIRMED", "RECONCILED"].includes(state);
}

export function App() {
  const stored = useMemo(() => readStoredCheckout(), []);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [customerName, setCustomerName] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(stored?.sessionId ?? null);
  const [observability, setObservability] = useState<ObservabilityIds | null>(null);
  const [error, setError] = useState<string | null>(null);
  const idempotencyKeyRef = useRef<string | null>(stored?.idempotencyKey ?? null);

  const sessionQuery = useSession(sessionId);
  const session = sessionQuery.data?.data ?? null;
  const catalogQuery = useCatalog();
  const { placeOrder } = useCheckoutMutations(setObservability);

  const products = useMemo(() => catalogQuery.data?.data ?? [], [catalogQuery.data]);
  const orderComplete = Boolean(session && isOrderComplete(session.state));
  const fulfillPending = session?.state === "FULFILL_PENDING";
  const checkoutBusy = placeOrder.isPending;

  useEffect(() => {
    if (orderComplete) {
      clearStoredCheckout();
    }
  }, [orderComplete]);

  useEffect(() => {
    setCart((current) => (current.length === 0 ? current : syncCartWithCatalog(current, products)));
  }, [products]);

  const runPlaceOrder = async (checkoutCart: CartItem[], existingSessionId?: string | null) => {
    if (checkoutCart.length === 0) {
      return;
    }
    setError(null);
    const idempotencyKey = idempotencyKeyRef.current ?? newIdempotencyKey();
    idempotencyKeyRef.current = idempotencyKey;
    try {
      const result = await placeOrder.mutateAsync({
        cart: checkoutCart,
        customerName: customerName.trim() || undefined,
        idempotencyKey,
        sessionId: existingSessionId ?? undefined,
      });
      writeStoredCheckout(result.data.sessionId, idempotencyKey);
      setSessionId(result.data.sessionId);
      if (isOrderComplete(result.data.state)) {
        setCart([]);
      }
    } catch (err) {
      if (isApiError(err) && err.status === 409) {
        void catalogQuery.refetch();
      }
      setError(isApiError(err) ? err.detail : "Could not place order");
    }
  };

  return (
    <div className="layout">
      <header className="header">
        <h1>Shop</h1>
        <p className="muted">Live inventory — one-click checkout.</p>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      {catalogQuery.isLoading && <p>Loading inventory…</p>}
      {catalogQuery.isError && (
        <p className="error" role="alert">
          Failed to load inventory
          {catalogQuery.error
            ? `: ${isApiError(catalogQuery.error) ? catalogQuery.error.detail : String(catalogQuery.error)}`
            : ""}
          .
        </p>
      )}

      {orderComplete && session && (
        <section className="panel order-complete" role="status">
          <h2>Order placed</h2>
          <p>
            Thank you{session.customerName ? `, ${session.customerName}` : ""}! Your order is{" "}
            <strong>PENDING</strong> in EC-OPS.
          </p>
          {session.orderId && (
            <p>
              Order ID: <code>{session.orderId}</code>
            </p>
          )}
          <p className="muted">
            Trace: correlation <code>{session.correlationId}</code>
          </p>
          <button
            type="button"
            className="primary"
            onClick={() => {
              setSessionId(null);
              idempotencyKeyRef.current = null;
              clearStoredCheckout();
            }}
          >
            Continue shopping
          </button>
        </section>
      )}

      {fulfillPending && session && (
        <section className="panel" role="alert">
          <h2>Finalizing your order</h2>
          <p>Order {session.orderId} was created. Retrying inventory commit…</p>
          <button
            type="button"
            className="primary"
            disabled={checkoutBusy}
            onClick={() => void runPlaceOrder([], session.sessionId)}
          >
            {checkoutBusy ? "Retrying…" : "Retry"}
          </button>
        </section>
      )}

      {!orderComplete && !fulfillPending && (
        <div className="main-grid">
          <div className="stack">
            <CatalogGrid
              products={products}
              cart={cart}
              onAdd={(item) => setCart((current) => addToCart(current, item))}
              disabled={checkoutBusy}
            />
            <CartPanel
              cart={cart}
              customerName={customerName}
              onCustomerNameChange={setCustomerName}
              onCartChange={setCart}
              onRemove={(sku) => setCart((current) => removeFromCart(current, sku))}
              onCheckout={(checkoutCart) => void runPlaceOrder(checkoutCart)}
              checkoutPending={checkoutBusy}
              disabled={false}
            />
          </div>

          <div className="stack">
            {session && !isOrderComplete(session.state) && session.state !== "FULFILL_PENDING" && (
              <section className="panel muted-panel">
                <h2>Checkout status</h2>
                <p>State: {session.state}</p>
              </section>
            )}
            <DevObservabilityPanel ids={observability} />
          </div>
        </div>
      )}

      {orderComplete && session && session.lineItems.length > 0 && (
        <section className="panel">
          <h3>Items</h3>
          <ul className="checkout-lines">
            {session.lineItems.map((line) => (
              <li key={line.sku}>
                {line.name} × {line.quantity} — {formatCurrency(line.unitPrice * line.quantity)}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
