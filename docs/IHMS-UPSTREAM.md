# KB-IHMS upstream integration (main branch)

Canonical API: `GET /api/inventory`, `POST /api/holds`, `DELETE /api/holds/{id}`.

## Real KB-IHMS main (July 2026)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/inventory` | Catalog + stock (`productId`, `name`, `availableQuantity`) |
| `POST /api/holds` | Atomic stock reservation (deducts inventory) |
| `DELETE /api/holds/{id}` | Release hold (restores stock) — compensation path |

**Not on main:** `GET /api/products`, `POST /api/holds/{id}/fulfill`. Orchestrator uses `ihms_catalog_mode=auto` (tries products, falls back to inventory).

## Orchestrator mapping

| IHMS field | Orchestrator |
|------------|--------------|
| `productId` | `ihms_product_id` |
| `name` | product title |
| `availableQuantity` | `available_quantity` |
| Prices / SKUs | `catalog/ihms-products.json` (orchestrator-owned) |
| EC-OPS line codes | `catalog/ecops-mapping.json` |

## Inventory on successful order

Real KB-IHMS deducts stock on **hold create**. On EC-OPS order success the orchestrator:

1. Calls `POST /api/holds/{id}/fulfill` when available (mock / Plan-A branch)
2. On **404** (real main): treat as success — stock already deducted, hold stays Active

**Do not** `DELETE` the hold after a successful order (that restores stock).

## Idempotency

| System | Behavior |
|--------|----------|
| IHMS `POST /api/holds` | **Not idempotent** — orchestrator holds once per session (`CREATED → HELD`) |
| EC-OPS `POST /orders` | `Idempotency-Key` + `client_reference` (session correlation) |
| Orchestrator | `POST /sessions/checkout` — single idempotency key for hold + order |

## Observability

IHMS **does not echo** trace headers (sent anyway for orchestrator logs). EC-OPS echoes `X-Request-ID`, `X-Correlation-ID`, `X-Trace-ID`.

Session `correlation_id` is used as `X-Correlation-ID` and EC-OPS `client_reference` for end-to-end trace.

## Docker

KB-IHMS: `docker compose up` → http://localhost:5000

```bash
IHMS_BASE_URL=http://host.docker.internal:5000  # orchestrator in Docker
```
