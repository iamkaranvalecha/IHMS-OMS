import { useMemo, useState } from "react";

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

export function App() {
  const [cart, setCart] = useState<CartItem | null>(null);
  const [customerName, setCustomerName] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [observability, setObservability] = useState<ObservabilityIds | null>(null);
  const [error, setError] = useState<string | null>(null);

  const catalogQuery = useCatalog();
  const sessionQuery = useSession(sessionId);
  const { startCheckout, confirmCheckout, abandonCheckout } = useCheckoutMutations(setObservability);

  const session = sessionQuery.data?.data ?? null;
  const checkoutActive = Boolean(session && !["CONFIRMED", "RECONCILED", "ABANDONED", "COMPENSATED"].includes(session.state));

  const products = useMemo(() => catalogQuery.data?.data ?? [], [catalogQuery.data]);

  const handleStartCheckout = async () => {
    if (!cart) {
      return;
    }
    setError(null);
    try {
      const result = await startCheckout.mutateAsync({ cart, customerName: customerName.trim() });
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
      await confirmCheckout.mutateAsync({ sessionId, idempotencyKey: newIdempotencyKey() });
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
