# IHMS-OMS — Checkout Orchestrator

**Distributed Checkout Platform** — integrates frozen assignment repos into a production-shaped checkout flow.

| Repo | Role |
|------|------|
| [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS) | .NET inventory hold microservice (frozen) |
| [EC-OPS](https://github.com/iamkaranvalecha/EC-OPS) | FastAPI order management system (frozen) |
| **IHMS-OMS** (this repo) | BFF, saga, CatalogProvider, UI, ADRs, observability |

## Quick start

```bash
pip install -e ".[dev]"
bash scripts/verify.sh
uvicorn src.main:app --reload --port 8000
curl http://localhost:8000/health
```

### React UI

```bash
uvicorn src.main:app --reload --port 8000   # terminal 1
cd frontend && cp .env.example .env && npm install && npm run dev   # terminal 2
```

Open http://localhost:5173

### Full stack (E2E demo)

```bash
bash scripts/e2e-stack.sh up
# orchestrator http://localhost:8000  |  UI http://localhost:5173
curl http://localhost:8000/metrics   # Prometheus counters
STACK=1 bash scripts/verify.sh        # runs unit + integration + e2e
bash scripts/e2e-stack.sh down
```

**Observability stack** (Prometheus scrapes `/metrics`):

```bash
bash scripts/obs-stack.sh up
# Prometheus UI http://localhost:9090
bash scripts/obs-stack.sh down
```

The full stack uses **wire-compatible mock upstreams** (`docker/mock-upstreams/`) so CI and local demos do not depend on external image registries. Optional real images:

```bash
IHMS_IMAGE=ghcr.io/iamkaranvalecha/kb-ihms:latest \
ECOPS_IMAGE=ghcr.io/iamkaranvalecha/ec-ops:latest \
docker compose -f docker/compose.base.yml -f docker/compose.full.yml up --build
```

## Architecture snapshot

```
Browser → React UI (nginx) → Orchestrator (FastAPI)
                                  ├→ KB-IHMS (holds)
                                  └→ EC-OPS (orders)
```

Saga states: `CREATED → HELD → CONFIRMED | ABANDONED | COMPENSATED | RECONCILED`

Key API routes:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + observability IDs |
| GET | `/metrics` | Prometheus saga counters |
| GET | `/catalog` | Product list |
| POST | `/sessions` | Start checkout session |
| POST | `/sessions/{id}/hold` | Reserve inventory |
| POST | `/sessions/{id}/confirm` | Place order (requires `Idempotency-Key`) |
| DELETE | `/sessions/{id}` | Abandon / release hold |

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
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Timeouts, retries, pooling |
| [docs/sequences/](docs/sequences/) | Per-flow sequence diagrams |
| [docs/adr/](docs/adr/) | Architectural decision records |
| [AI-USAGE.md](AI-USAGE.md) | AI transparency log |

## Docker

```bash
# Orchestrator only (lightweight dev)
docker compose -f docker/compose.base.yml -f docker/compose.dev.yml up

# Full stack demo + E2E
docker compose -f docker/compose.base.yml -f docker/compose.full.yml up --build

# Full stack + Prometheus (Phase 6 observability)
docker compose -f docker/compose.base.yml -f docker/compose.full.yml \
  -f docker/compose.observability.yml --profile obs up --build
```

Orchestrator containers default to `LOG_JSON=true` (structured JSON on stdout). UI nginx proxies `/health` and `/metrics`.

## Project tracking

- GitHub Issues with label `integration/oms`
- [Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1)

## Status

**Phase 5 complete (v0.5.0)** — full-stack E2E with mock upstreams, React UI, and saga orchestration. See [ROADMAP.md](ROADMAP.md) for history.
