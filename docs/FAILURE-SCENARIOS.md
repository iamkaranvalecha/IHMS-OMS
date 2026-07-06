# Failure Scenarios

Matrix of failure modes, detection, actions, and sequence documentation. Saga logic lives in `src/saga/` only.

| Scenario | Detection | Action | Sequence |
|----------|-----------|--------|----------|
| Hold fails (409/404) | IHMS response | Fail early; no hold on session | [checkout.md](sequences/checkout.md) |
| Order fails after hold | EC-OPS 4xx/5xx | Compensate: DELETE hold | [compensation.md](sequences/compensation.md) |
| Hold expires before confirm | IHMS 409 / countdown | Block confirm | [expiry.md](sequences/expiry.md) |
| Upstream unavailable | timeout / 503 | Fail or limited retry per [PERFORMANCE.md](PERFORMANCE.md) | — |
| Duplicate confirm | Idempotency key | Cached response | [checkout.md](sequences/checkout.md) |
| Inventory finalization fails after order | IHMS fulfill timeout / 5xx after EC-OPS order success | Session → `FULFILL_PENDING` with `order_id`; retry confirm with same idempotency key finalizes hold (no duplicate order) | [checkout.md](sequences/checkout.md) |
| Insufficient stock at hold | Orchestrator pre-check or IHMS 409 | Fail early; session stays `CREATED` | [checkout.md](sequences/checkout.md) |
| Partial success after timeout | httpx timeout on `POST /orders` | Reconcile by client reference; compensate only after a successful lookup with no trusted match; retain hold if lookup fails | [reconciliation.md](sequences/reconciliation.md) |

## Reconciliation summary

When `POST /orders` times out, order creation is **unknown**:

1. Query EC-OPS for order by client reference / correlation / idempotency key.
2. If found → attach `order_id`, complete session.
3. If lookup succeeds and no trusted match exists → safe to compensate (release hold) or retry with same idempotency key.
4. If lookup fails → retain the hold and return 503; retry with the original idempotency key to reconcile before any new order create.

Detail: [sequences/reconciliation.md](sequences/reconciliation.md).

## Test coverage expectation

Each row must have corresponding tests by Phase 3 (integration) and Phase 5 (e2e where applicable).

| Scenario | Integration | E2E |
|----------|-------------|-----|
| Hold fails 409 | `test_hold_fails_with_409` | `test_hold_fails_with_409` |
| Order fails → compensate | `test_confirm_compensates_*`, `test_one_click_checkout_compensates_*` | `test_confirm_compensates_when_order_fails` |
| Hold expires | unit `test_confirm_rejects_expired_hold` | — |
| Duplicate confirm / place-order | `test_duplicate_confirm_*`, `test_place_order_idempotency_replay` | `test_place_order_idempotency_replay` |
| FULFILL_PENDING | `test_confirm_fulfill_pending_then_retry` | — |
| Insufficient stock | `test_hold_rejected_when_inventory_insufficient` | — |
| Reconciliation timeout | `test_reconcile_after_order_timeout` | `test_reconcile_after_order_timeout` |
| EC-OPS auth failure | `test_health_upstreams_auth_failure_*` | `test_health_upstreams` |

Full workflow suite: `tests/integration/test_full_workflow.py`
