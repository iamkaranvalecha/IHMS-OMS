# EC-OPS upstream integration (PR #24)

Canonical contract lives in the **EC-OPS repo**: [`docs/orchestrator-handoff.md`](https://github.com/iamkaranvalecha/EC-OPS/blob/main/docs/orchestrator-handoff.md).

PR [#24](https://github.com/iamkaranvalecha/EC-OPS/pull/24) merged the orchestrator order contract (from PR #23) with Orders UI, Docker Compose, and migration fixes. **No new orchestrator API changes** beyond PR #23 — IHMS-OMS Plan C already targets this contract.

## What EC-OPS provides

| Capability | EC-OPS endpoint | IHMS-OMS usage |
|------------|-----------------|----------------|
| Auth | `POST /auth/token` (form body) | `scripts/ecops-token.sh` → `ECOPS_BEARER_TOKEN` |
| Create order | `POST /orders` + `Idempotency-Key` | Saga confirm step |
| Idempotent replay | **200** same order | `EcOpsClient.create_order` (200 = success) |
| First create | **201** | Same |
| Duplicate `client_reference` | **409** | Pre-lookup + reconcile on 409 race |
| Idempotency conflict | **409** (different body) | Fail / compensate |
| Reconciliation | `GET /orders?client_reference=` | `find_order_by_client_reference` |
| Trace headers | `X-Request-ID`, `X-Correlation-ID`, `X-Trace-ID` | Propagated on all outbound calls |

## Required migrations (EC-OPS side)

Before orchestrator traffic against a real EC-OPS database:

- `0005_add_client_reference` — unique `client_reference` column
- `0006_add_order_idempotency_keys` — 24h idempotency store

Docker EC-OPS runs `scripts/migrate.py` automatically on startup.

## Local EC-OPS (Docker)

```bash
cd ../EC-OPS
docker compose up -d --build
curl http://localhost:8002/health
```

Default seeded user: `admin` / `Password1!` (see EC-OPS `docker/entrypoint.sh`).

Fetch token into IHMS-OMS `.env`:

```bash
ECOPS_USERNAME=admin ECOPS_PASSWORD='Password1!' bash scripts/ecops-token.sh
```

## IHMS-OMS mapping

| Orchestrator field | EC-OPS field |
|--------------------|--------------|
| `session.correlation_id` | `client_reference` |
| Confirm `Idempotency-Key` header | `Idempotency-Key` on `POST /orders` |
| `ecops_item_code` from catalog | `items[].product_name` |
| Line `unit_price` | `items[].price` |

SKU → EC-OPS product name mapping: `catalog/ecops-mapping.json` (thin config; EC-OPS has no catalog).

## Out of scope (orchestrator owns)

- IHMS holds / inventory validation
- EC-OPS stock checks
- Webhooks — poll `GET /orders/{id}` if needed
- Token refresh — re-login before 24h JWT expiry

## Design references (EC-OPS repo)

| Document | Topic |
|----------|-------|
| `docs/orchestrator-handoff.md` | Integrator contract |
| `DESIGN_DECISIONS.md` §17 | Idempotency + client_reference ADR |
| `ARCHITECTURE.md` | Orchestrator integration section |
| `tests/integration/test_orchestrator_orders.py` | 11 contract tests |

## Mock parity

`docker/mock-upstreams/ecops/` mirrors POST idempotency (201/200/409), `client_reference` filter on GET, and duplicate `client_reference` → 409.
