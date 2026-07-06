# Sequence: Checkout (Happy Path)

**Use cases:** UC-3 (browse/add), UC-5 (confirm order)

**Status:** Implemented (Phase 3+)

## Actors

- User / UI
- Orchestrator API
- CatalogProvider
- KB-IHMS
- EC-OPS

## One-click flow (v0.11 UI default)

The shop UI calls a single endpoint instead of session → hold → confirm:

```mermaid
sequenceDiagram
  participant UI
  participant API as Orchestrator
  participant IHMS as KB-IHMS
  participant OPS as EC-OPS

  UI->>API: GET /catalog
  API->>IHMS: GET /api/inventory
  IHMS-->>API: stock
  API-->>UI: products

  UI->>API: POST /sessions/checkout + Idempotency-Key, items[]
  API->>IHMS: POST /api/holds
  IHMS-->>API: hold_id
  API->>OPS: POST /orders
  OPS-->>API: order_id
  API-->>UI: CONFIRMED
```

API: `POST /sessions/{id}/place-order` — same saga when a session already exists.

See [WORKFLOWS.md](../WORKFLOWS.md) for full diagrams.

```mermaid
sequenceDiagram
  participant UI
  participant API as Orchestrator
  participant CAT as Catalog
  participant IHMS as KB-IHMS
  participant OPS as EC-OPS

  UI->>API: GET /catalog
  API->>IHMS: GET /api/inventory
  IHMS-->>API: stock levels
  API-->>UI: products with available_quantity

  UI->>API: POST /sessions
  API-->>UI: session_id, correlation_id

  UI->>API: POST /sessions/{id}/hold items[]
  API->>CAT: resolve SKUs
  API->>IHMS: POST /api/holds items[]
  IHMS-->>API: hold_id, expires_at
  API-->>UI: HELD, line_items[]

  UI->>API: POST /sessions/{id}/confirm Idempotency-Key
  API->>OPS: POST /orders items[]
  OPS-->>API: order_id
  API->>IHMS: POST /api/holds/{id}/fulfill
  IHMS-->>API: fulfilled
  API-->>UI: CONFIRMED
```

## Fulfill pending branch

When EC-OPS creates the order but IHMS fulfill fails after retries:

1. Session moves to `FULFILL_PENDING` with `order_id` set.
2. API returns 200; UI shows retry finalize.
3. Retry confirm with the **same** `Idempotency-Key` — no duplicate EC-OPS order.
4. Abandon is blocked until fulfill completes or ops intervenes.

## Failure branches

See [FAILURE-SCENARIOS.md](../FAILURE-SCENARIOS.md) — hold fail, duplicate confirm, fulfill pending, reconciliation.

## Phase gate

- [x] Integration test covers happy path
- [x] Idempotency key cached on duplicate confirm
- [x] Multi-item hold + confirm integration test
- [x] Fulfill pending retry integration test
- [x] One-click checkout (`POST /sessions/checkout`) integration + e2e
- [x] Place order on session (`POST /sessions/{id}/place-order`) integration + e2e
