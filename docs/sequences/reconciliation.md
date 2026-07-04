# Sequence: Reconciliation After Timeout

**Scenario:** `POST /orders` times out — order may or may not exist

**Status:** Implemented (Phase 3)

## Problem

```text
POST /orders → timeout → order created? UNKNOWN
```

This is the classic ambiguous outcome in distributed systems.

## Reconciliation flow

```mermaid
sequenceDiagram
  participant API as Orchestrator
  participant OPS as EC-OPS
  participant IHMS as KB-IHMS

  API->>OPS: POST /orders
  Note over API,OPS: timeout — no response

  API->>OPS: GET /orders
  Note over API: only accept a returned order with matching client_reference
  alt Matching order found
    OPS-->>API: order_id
    Note over API: Session → RECONCILED / CONFIRMED
  else Matching order not found
    OPS-->>API: no trusted match
    API->>IHMS: DELETE /api/holds/{hold_id}
    Note over API: COMPENSATED; no blind POST retry
  end
```

## Decision rules

1. **Trusted match found** → attach `order_id`, complete session; do not release hold.
2. **No trusted match** → compensate the hold and surface the ambiguous timeout.
3. Log `step: reconcile` with all IDs for audit.

See [ADR-008](../adr/ADR-008-reconciliation-timeout.md).
