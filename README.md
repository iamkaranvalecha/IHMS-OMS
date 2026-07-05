# IHMS-OMS — Checkout Orchestrator

**Distributed Checkout Platform** — integrates frozen assignment repos into a production-shaped checkout flow.

| Repo | Role |
|------|------|
| [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS) | .NET inventory hold microservice (frozen) |
| [EC-OPS](https://github.com/iamkaranvalecha/EC-OPS) | FastAPI order management system (frozen) |
| **IHMS-OMS** (this repo) | BFF, saga, CatalogProvider, UI, ADRs, observability |

## Quick start (Docker)

From the repository root:

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Checkout UI | http://localhost:5180 |
| Orchestrator | http://localhost:8000 |
| Swagger / metrics | http://localhost:8000/docs · http://localhost:8000/metrics |

Stop: `docker compose down`

Prometheus: `docker compose --profile obs up --build` → http://localhost:9090

The default stack uses **wire-compatible mock upstreams** (`docker/mock-upstreams/`) so CI and local demos need no sibling repos. To point at real [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS) + [EC-OPS](https://github.com/iamkaranvalecha/EC-OPS), see [docs/DOCKER.md](docs/DOCKER.md).

### Local dev (no Docker)

```bash
pip install -e ".[dev]"
bash scripts/verify.sh
uvicorn src.main:app --reload --port 8000
curl http://localhost:8000/health
```

### React UI (dev server)

```bash
uvicorn src.main:app --reload --port 8000   # terminal 1
cd frontend && cp .env.example .env && npm install && npm run dev   # terminal 2
```

Open http://localhost:5173

### E2E tests

```bash
STACK=1 bash scripts/verify.sh
```

## Architecture snapshot

```
Browser → React UI (nginx) → Orchestrator (FastAPI)
                                  ├→ KB-IHMS (holds)
                                  └→ EC-OPS (orders)
```

Saga states: `CREATED → HELD → CONFIRMED | FULFILL_PENDING → CONFIRMED | ABANDONED | COMPENSATED | RECONCILED`

Key API routes:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + observability IDs |
| GET | `/metrics` | Prometheus saga counters |
| GET | `/catalog` | Product list with live IHMS stock (`available_quantity`; `null` when IHMS inventory is unavailable) |
| POST | `/sessions` | Start checkout session |
| POST | `/sessions/{id}/hold` | Reserve inventory for one or more cart lines |
| POST | `/sessions/{id}/confirm` | Place order (requires `Idempotency-Key`) |
| DELETE | `/sessions/{id}` | Abandon / release hold |

Hold request body (multi-item cart):

```json
{
  "customer_name": "Jane Doe",
  "items": [
    { "sku": "WIDGET-001", "quantity": 2 },
    { "sku": "GADGET-002", "quantity": 1 }
  ]
}
```

All lines are sent in a single atomic IHMS hold. Confirm maps every held line to EC-OPS order items.

**Catalog sources:** Default `CATALOG_SOURCE=json` uses `catalog/products.json` (mock stack). For real KB-IHMS, set `CATALOG_SOURCE=ihms` — the orchestrator calls `GET /api/products` and maps SKUs to EC-OPS line codes via `catalog/ecops-mapping.json` (defaults to same SKU).

## Documentation map

| Document | Purpose |
|----------|---------|
| [ROADMAP.md](ROADMAP.md) | Phase gates and delivery status |
| [AGENTS.md](AGENTS.md) | Agent/human contributor guide |
| [CLAUDE.md](CLAUDE.md) | Slim AI entry point |
| [docs/DECISION-MATRIX.md](docs/DECISION-MATRIX.md) | 60-second architecture |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module layout and boundaries |
| [docs/FAILURE-SCENARIOS.md](docs/FAILURE-SCENARIOS.md) | Failure matrix |
| [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md) | Request / Correlation / Trace IDs |
| [docs/DOCKER.md](docs/DOCKER.md) | Deploy stack vs mock E2E |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Timeouts, retries, pooling |
| [docs/sequences/](docs/sequences/) | Per-flow sequence diagrams |
| [docs/adr/](docs/adr/) | Architectural decision records |
| [AI-USAGE.md](AI-USAGE.md) | AI transparency log |

## Docker

```bash
docker compose up --build          # full stack
docker compose --profile obs up    # + Prometheus
docker compose down
```

E2E/CI uses `scripts/e2e-stack.sh` (wraps the same compose file). Details: [docs/DOCKER.md](docs/DOCKER.md).

## Project tracking

- GitHub Issues with label `integration/oms`
- [Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1)

## Status

**v0.7.1** — single `docker-compose.yml` (KB-IHMS pattern). See [ROADMAP.md](ROADMAP.md).
