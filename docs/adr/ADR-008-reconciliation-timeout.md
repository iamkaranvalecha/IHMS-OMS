# ADR-008: Reconciliation After Ambiguous Timeout

**Status:** Accepted  
**Date:** 2026-07-04

## Context

When `POST /orders` times out, the order may have been created. Blind retry risks duplicates; blind compensation risks cancelling a successful order.

## Decision

Attempt reconciliation after a timeout, but only trust an order that carries a
matching client reference in the EC-OPS response. The frozen EC-OPS API does not
persist `client_reference` or enforce `Idempotency-Key`, so the orchestrator must
not attach an unfiltered list result or retry `POST /orders` blindly.

## Consequences

- `src/saga/steps/reconcile.py` handles the unknown-outcome path.
- EC-OPS list/filter or client reference field is required for successful reconciliation.
- If reconciliation succeeds but returns no trusted match, the orchestrator compensates the hold and returns an ambiguous timeout error instead of risking duplicate orders.
- If reconciliation itself fails, the orchestrator retains the hold and returns 503 because releasing inventory while an order may exist would create order/hold divergence.
- Documented in [sequences/reconciliation.md](../sequences/reconciliation.md).

## Open questions

- Exact EC-OPS query API for idempotency lookup remains unavailable in the frozen upstream. A future additive EC-OPS contract could expose `client_reference` filtering or order-create idempotency.
