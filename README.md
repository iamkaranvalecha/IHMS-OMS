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

## Documentation map

| Document | Purpose |
|----------|---------|
| [ROADMAP.md](ROADMAP.md) | Current phase and delivery gates |
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

# Full stack demo (Phase 5)
docker compose -f docker/compose.base.yml -f docker/compose.full.yml up --build
```

## Project tracking

- GitHub Issues with label `integration/oms`
- [Project #4](https://github.com/users/iamkaranvalecha/projects/4)

## Status

**Phase 1 — Scaffold** (see [ROADMAP.md](ROADMAP.md))

Phase 2+ will add gateway clients, saga flows, React UI, and full-stack E2E.
