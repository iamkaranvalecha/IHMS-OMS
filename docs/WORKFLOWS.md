# Checkout Workflows

End-to-end flows for IHMS-OMS v0.11. For failure branches see [FAILURE-SCENARIOS.md](FAILURE-SCENARIOS.md).

---

## One-click checkout (production UI)

```mermaid
sequenceDiagram
  autonumber
  participant UI as Shop UI
  participant API as Orchestrator
  participant IHMS as KB-IHMS
  participant OPS as EC-OPS

  UI->>API: GET /catalog
  API->>IHMS: GET /api/inventory
  IHMS-->>API: stock
  API-->>UI: products

  UI->>API: POST /sessions/checkout + Idempotency-Key
  API->>IHMS: POST /api/holds
  IHMS-->>API: hold_id
  API->>OPS: POST /orders
  OPS-->>API: order_id
  API->>IHMS: POST fulfill (404 OK on real main)
  API-->>UI: CONFIRMED
```

---

## Place order on existing session

```mermaid
sequenceDiagram
  participant Client
  participant API as Orchestrator
  participant IHMS as KB-IHMS
  participant OPS as EC-OPS

  Client->>API: POST /sessions
  Client->>API: POST /sessions/{id}/place-order + Idempotency-Key
  alt CREATED
    API->>IHMS: POST /api/holds
  end
  API->>OPS: POST /orders
  API-->>Client: CONFIRMED
```

---

## Saga state machine

```mermaid
stateDiagram-v2
  [*] --> CREATED
  CREATED --> HELD: place_hold / place_order
  HELD --> CONFIRMED: confirm / place_order success
  HELD --> FULFILL_PENDING: order OK, fulfill retry
  FULFILL_PENDING --> CONFIRMED: retry confirm
  HELD --> COMPENSATED: order fail
  HELD --> RECONCILED: timeout + lookup hit
  HELD --> ABANDONED: DELETE session
  CREATED --> ABANDONED: DELETE session
```

---

## Stack modes

| Mode | Script / task | Upstreams |
|------|---------------|-----------|
| Mock | `dev-up.ps1`, **Cursor: Quick start mock** | Containers in compose |
| Real | `real-upstream.ps1`, **Cursor: Real dev environment** | KB-IHMS + EC-OPS on host |

---

## Test coverage

| Workflow | Integration | E2E |
|----------|-------------|-----|
| One-click | `test_one_click_checkout` | `test_one_click_checkout` |
| Place order | `test_place_order_on_existing_session` | `test_place_order_on_existing_session` |
| Idempotency | `test_place_order_idempotency_replay` | `test_place_order_idempotency_replay` |
| Hold → confirm | `test_happy_path_hold_and_confirm` | `test_happy_path_hold_and_confirm` |
| Compensation | `test_one_click_checkout_compensates_*` | `test_confirm_compensates_*` |
| Upstream health | `test_health_upstreams_*` | `test_health_upstreams` |
