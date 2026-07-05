import { useEffect, useMemo, useRef, useState } from "react";

import { useCatalog, useCheckoutMutations, useSession } from "@/api/hooks";
import { isApiError } from "@/api/types";
import type { CartItem, ObservabilityIds } from "@/api/types";
import { CartPanel } from "@/components/CartPanel";
import { CatalogGrid } from "@/components/CatalogGrid";
import { CheckoutPanel } from "@/components/CheckoutPanel";
import { DevObservabilityPanel } from "@/components/DevObservabilityPanel";

function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

const ACTIVE_CHECKOUT_STORAGE_KEY = "checkout-orchestrator.active-checkout";

interface StoredActiveCheckout {
  sessionId: string;
  confirmIdempotencyKey: string;
}

function readStoredActiveCheckout(): StoredActiveCheckout | null {
  try {
    const raw = window.sessionStorage.getItem(ACTIVE_CHECKOUT_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<StoredActiveCheckout>;
    if (parsed.sessionId && parsed.confirmIdempotencyKey) {
      return {
        sessionId: parsed.sessionId,
        confirmIdempotencyKey: parsed.confirmIdempotencyKey,
      };
    }
  } catch {
    // Storage can be unavailable in restricted browser contexts.
  }
  return null;
}

function writeStoredActiveCheckout(sessionId: string, confirmIdempotencyKey: string): void {
  try {
    window.sessionStorage.setItem(
      ACTIVE_CHECKOUT_STORAGE_KEY,
      JSON.stringify({ sessionId, confirmIdempotencyKey }),
    );
  } catch {
    // A volatile in-memory key still protects same-page retries.
  }
}

function clearStoredActiveCheckout(): void {
  try {
    window.sessionStorage.removeItem(ACTIVE_CHECKOUT_STORAGE_KEY);
  } catch {
    // Nothing to clear when storage is unavailable.
  }
}

function isTerminalState(state: string): boolean {
  return ["CONFIRMED", "RECONCILED", "ABANDONED", "COMPENSATED"].includes(state);
}

export function App() {
  const storedActiveCheckout = useMemo(() => readStoredActiveCheckout(), []);
  const [cart, setCart] = useState<CartItem | null>(null);
  const [customerName, setCustomerName] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(
    storedActiveCheckout?.sessionId ?? null,
  );
  const [observability, setObservability] = useState<ObservabilityIds | null>(null);
  const [error, setError] = useState<string | null>(null);
  const confirmIdempotencyKeyRef = useRef<string | null>(
    storedActiveCheckout?.confirmIdempotencyKey ?? null,
  );

  const catalogQuery = useCatalog();
  const sessionQuery = useSession(sessionId);
  const { startCheckout, confirmCheckout, abandonCheckout } = useCheckoutMutations(setObservability);

  const session = sessionQuery.data?.data ?? null;
  const checkoutActive = Boolean(session && !isTerminalState(session.state));

  const products = useMemo(() => catalogQuery.data?.data ?? [], [catalogQuery.data]);

  useEffect(() => {
    if (session && isTerminalState(session.state)) {
      clearStoredActiveCheckout();
    }
  }, [session]);

  const handleStartCheckout = async () => {
    if (!cart) {
      return;
    }
    setError(null);
    try {
      const result = await startCheckout.mutateAsync({ cart, customerName: customerName.trim() });
      const confirmIdempotencyKey = newIdempotencyKey();
      confirmIdempotencyKeyRef.current = confirmIdempotencyKey;
      writeStoredActiveCheckout(result.data.sessionId, confirmIdempotencyKey);
      setSessionId(result.data.sessionId);
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Checkout failed");
    }
  };

  const handleConfirm = async () => {
    if (!sessionId) {
      return;
    }
    setError(null);
    try {
      const idempotencyKey = confirmIdempotencyKeyRef.current ?? newIdempotencyKey();
      confirmIdempotencyKeyRef.current = idempotencyKey;
      writeStoredActiveCheckout(sessionId, idempotencyKey);
      const result = await confirmCheckout.mutateAsync({ sessionId, idempotencyKey });
      if (isTerminalState(result.data.state)) {
        clearStoredActiveCheckout();
      }
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Confirm failed");
    }
  };

  const handleAbandon = async () => {
    if (!sessionId) {
      return;
    }
    setError(null);
    try {
      await abandonCheckout.mutateAsync(sessionId);
      clearStoredActiveCheckout();
      setCart(null);
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Abandon failed");
    }
  };

  return (
    <div className="layout">
      <header className="header">
        <h1>Checkout Orchestrator</h1>
        <p className="muted">Browse inventory, place a hold, confirm or abandon.</p>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      {catalogQuery.isLoading && <p>Loading catalog…</p>}
      {catalogQuery.isError && <p className="error">Failed to load catalog.</p>}

      <div className="main-grid">
        <div className="stack">
          <CatalogGrid
            products={products}
            cart={cart}
            onAdd={setCart}
            disabled={checkoutActive || startCheckout.isPending}
          />
          <CartPanel
            cart={cart}
            customerName={customerName}
            onCustomerNameChange={setCustomerName}
            onRemove={() => setCart(null)}
            onCheckout={() => void handleStartCheckout()}
            checkoutPending={startCheckout.isPending}
            disabled={checkoutActive}
          />
        </div>

        <div className="stack">
          {session && (
            <CheckoutPanel
              session={session}
              onConfirm={() => void handleConfirm()}
              onAbandon={() => void handleAbandon()}
              confirmPending={confirmCheckout.isPending}
              abandonPending={abandonCheckout.isPending}
            />
          )}
          <DevObservabilityPanel ids={observability} />
        </div>
      </div>
    </div>
  );
}
