# Failure Scenarios

Matrix of failure modes, detection, actions, and sequence documentation. Saga logic lives in `src/saga/` only.

| Scenario | Detection | Action | Sequence |
|----------|-----------|--------|----------|
| Hold fails (409/404) | IHMS response | Fail early; no hold on session | [checkout.md](sequences/checkout.md) |
| Order fails after hold | EC-OPS 4xx/5xx | Compensate: DELETE hold | [compensation.md](sequences/compensation.md) |
| Hold expires before confirm | IHMS 409 / countdown | Block confirm | [expiry.md](sequences/expiry.md) |
| Upstream unavailable | timeout / 503 | Fail or limited retry per [PERFORMANCE.md](PERFORMANCE.md) | — |
| Duplicate confirm | Idempotency key | Cached response | [checkout.md](sequences/checkout.md) |
| Partial success after timeout | httpx timeout on `POST /orders` | Reconcile by client reference; compensate only after a successful lookup with no trusted match; retain hold if lookup fails | [reconciliation.md](sequences/reconciliation.md) |

## Reconciliation summary

When `POST /orders` times out, order creation is **unknown**:

1. Query EC-OPS for order by client reference / correlation / idempotency key.
2. If found → attach `order_id`, complete session.
3. If lookup succeeds and no trusted match exists → safe to compensate (release hold) or retry with same idempotency key.
4. If lookup fails → retain the hold and return 503 because order status is still unknown.

Detail: [sequences/reconciliation.md](sequences/reconciliation.md).

## Test coverage expectation

Each row must have corresponding tests by Phase 3 (integration) and Phase 5 (e2e where applicable).
