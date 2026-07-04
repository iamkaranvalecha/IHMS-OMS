# ADR-008: Reconciliation After Ambiguous Timeout

**Status:** Proposed (Phase 3)  
**Date:** 2026-07-04

## Context

When `POST /orders` times out, the order may have been created. Blind retry risks duplicates; blind compensation risks cancelling a successful order.

## Decision

Implement reconciliation query: look up order by correlation / idempotency key before compensating.

## Consequences

- `src/saga/reconciliation.py` handles unknown-outcome path.
- EC-OPS list/filter or client reference field required (verify in Phase 2 contract tests).
- Documented in [sequences/reconciliation.md](../sequences/reconciliation.md).

## Open questions

- Exact EC-OPS query API for idempotency lookup — confirm during gateway implementation.
