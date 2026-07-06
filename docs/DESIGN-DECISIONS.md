# Design Decisions

Index of architectural decisions. Full rationale: [adr/](adr/).

| ID | Decision | Rationale |
|----|----------|-----------|
| [ADR-001](adr/ADR-001-separate-orchestrator-repo.md) | Separate orchestrator repo | Frozen upstreams; integration here |
| [ADR-002](adr/ADR-002-catalog-provider.md) | CatalogProvider | Anti-corruption for SKUs/stock |
| [ADR-003](adr/ADR-003-mapping-not-in-upstreams.md) | Mapping in orchestrator | `catalog/*.json` not in IHMS/EC-OPS |
| [ADR-004](adr/ADR-004-saga-compensation.md) | Saga + compensation | Order fail → release hold |
| [ADR-005](adr/ADR-005-rest-first.md) | REST-first | HTTP before RabbitMQ events |
| [ADR-006](adr/ADR-006-observability-ids.md) | Triple observability IDs | Request / Correlation / Trace |
| [ADR-007](adr/ADR-007-module-split.md) | Strict module split | Gateway-only upstream HTTP |
| [ADR-008](adr/ADR-008-reconciliation-timeout.md) | Reconciliation | Lookup after EC-OPS timeout |

## v0.11 additions (no separate ADR)

| Decision | Choice |
|----------|--------|
| Default UI | One-click `POST /sessions/checkout` |
| Real IHMS catalog | Inventory API + `ihms-products.json` prices |
| Fulfill 404 | Success (stock already deducted on hold) |
| EC-OPS auth | JWT + `refresh-ecops-token` + force-recreate orchestrator |
| Windows DX | PowerShell 7, Cursor tasks, Docker-only stack |

See [DECISION-MATRIX.md](DECISION-MATRIX.md) and [WORKFLOWS.md](WORKFLOWS.md).
