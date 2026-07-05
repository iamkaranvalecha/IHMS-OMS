# Sequence: Checkout (Happy Path)

**Use cases:** UC-3 (browse/add), UC-5 (confirm order)

**Status:** Implemented (Phase 3)

## Actors

- User / UI
- Orchestrator API
- CatalogProvider
- KB-IHMS
- EC-OPS

## Flow

```mermaid
sequenceDiagram
  participant UI
  participant API as Orchestrator
  participant CAT as Catalog
  participant IHMS as KB-IHMS
  participant OPS as EC-OPS

  UI->>API: POST /sessions (create checkout)
  API-->>UI: session_id, correlation_id

  UI->>API: POST /sessions/{id}/hold
  API->>CAT: resolve SKU → ihms_product_id
  API->>IHMS: POST /api/holds
  IHMS-->>API: hold_id, expires_at
  API-->>UI: held, countdown

  UI->>API: POST /sessions/{id}/confirm (Idempotency-Key)
  API->>CAT: resolve SKU → ecops_item_code
  API->>OPS: POST /orders
  OPS-->>API: order_id
  API->>IHMS: POST /api/holds/{hold_id}/fulfill
  IHMS-->>API: fulfilled
  API-->>UI: confirmed
```

## Failure branches

See [FAILURE-SCENARIOS.md](../FAILURE-SCENARIOS.md) — hold fail, duplicate confirm,
and inventory finalization after order success.

When EC-OPS creates the order but IHMS fulfill fails, the session stays `HELD` with
the original `Idempotency-Key`. A retry with that key reconciles the existing order
before attempting fulfillment again, so checkout does not create a duplicate order
or report completion while inventory is still restorable.

## Phase gate

- [ ] Integration test covers happy path
- [ ] Idempotency key cached on duplicate confirm
