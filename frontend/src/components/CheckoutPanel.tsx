import { useState } from "react";

import { isHoldExpired, formatCurrency } from "@/api/normalize";
import type { CheckoutSession } from "@/api/types";
import { HoldCountdown } from "./HoldCountdown";

interface CheckoutPanelProps {
  session: CheckoutSession;
  onConfirm: () => void;
  onAbandon: () => void;
  confirmPending: boolean;
  abandonPending: boolean;
}

export function CheckoutPanel({
  session,
  onConfirm,
  onAbandon,
  confirmPending,
  abandonPending,
}: CheckoutPanelProps) {
  const [showAbandonConfirm, setShowAbandonConfirm] = useState(false);
  const expired = isHoldExpired(session.expiresAt);
  const terminal = ["CONFIRMED", "RECONCILED", "ABANDONED", "COMPENSATED"].includes(
    session.state,
  );

  if (terminal) {
    return (
      <section className="panel checkout-panel">
        <h2>Checkout complete</h2>
        <p>
          State: <strong>{session.state}</strong>
        </p>
        {session.orderId && (
          <p>
            Order: <code>{session.orderId}</code>
          </p>
        )}
      </section>
    );
  }

  if (session.state === "FULFILL_PENDING") {
    return (
      <section className="panel checkout-panel">
        <h2>Finalizing order</h2>
        <p>
          Order <code>{session.orderId}</code> was placed. Committing inventory hold…
        </p>
        <button type="button" className="primary" disabled={confirmPending} onClick={onConfirm}>
          {confirmPending ? "Retrying…" : "Retry finalize"}
        </button>
      </section>
    );
  }

  return (
    <section className="panel checkout-panel">
      <h2>Checkout</h2>
      <p>
        Session: <code>{session.sessionId}</code>
      </p>
      <p>
        State: <strong>{session.state}</strong>
      </p>
      {session.state === "HELD" && (
        <>
          {session.lineItems.length > 0 && (
            <ul className="checkout-lines">
              {session.lineItems.map((line) => (
                <li key={line.sku}>
                  {line.name} × {line.quantity} — {formatCurrency(line.unitPrice * line.quantity)}
                </li>
              ))}
            </ul>
          )}
          <HoldCountdown expiresAt={session.expiresAt} />
          <button
            type="button"
            className="primary"
            disabled={confirmPending || expired}
            onClick={onConfirm}
          >
            {confirmPending ? "Confirming…" : "Confirm order"}
          </button>
          {!showAbandonConfirm ? (
            <button
              type="button"
              className="secondary"
              disabled={abandonPending}
              onClick={() => setShowAbandonConfirm(true)}
            >
              Abandon checkout
            </button>
          ) : (
            <div className="confirm-dialog" role="alertdialog" aria-labelledby="abandon-title">
              <p id="abandon-title">Release hold and abandon this checkout?</p>
              <div className="button-row">
                <button
                  type="button"
                  className="danger"
                  disabled={abandonPending}
                  onClick={() => {
                    setShowAbandonConfirm(false);
                    onAbandon();
                  }}
                >
                  {abandonPending ? "Abandoning…" : "Yes, abandon"}
                </button>
                <button type="button" onClick={() => setShowAbandonConfirm(false)}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
