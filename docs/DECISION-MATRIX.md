# Decision Matrix

60-second architecture reference for the checkout platform. Canonical copy lives in this repo.

## Three-repo ecosystem

| Repo | Role | Changes |
|------|------|---------|
| [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS) | Inventory hold authority | Frozen — docs/rules only |
| [EC-OPS](https://github.com/iamkaranvalecha/EC-OPS) | Order lifecycle (OMS) | Frozen — no integration code |
| [IHMS-OMS](https://github.com/iamkaranvalecha/IHMS-OMS) (checkout-orchestrator) | BFF, saga, catalog, UI | All integration work |

## Requirements → solutions

| Requirement | Solution | Why |
|-------------|----------|-----|
| Inventory reservation | KB-IHMS | Source of truth for holds |
| Order lifecycle | EC-OPS | Existing OMS assignment |
| Integration | checkout-orchestrator | Loose coupling; frozen upstreams |
| Product mapping | CatalogProvider | Anti-corruption layer |
| Distributed consistency | Saga + compensation | Order fail → release hold |
| Communication | REST (Phase 1–4) | Simplicity; both upstreams expose HTTP |
| Future events | RabbitMQ consumer (Phase 5 stretch) | IHMS already publishes hold events |
| Observability | Request + Correlation + Trace IDs | Debug + future distributed tracing |
| Unknown after timeout | Reconciliation query | Classic distributed-systems problem |

## Module dependency rule

```
api → checkout → saga + session + catalog → gateway
```

- **gateway/** is the ONLY layer that calls KB-IHMS or EC-OPS.
- **UI** calls orchestrator API only.
- **catalog/** maps SKUs to upstream identifiers — mapping never lives in frozen repos.

## Related documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — module layout and boundaries
- [FAILURE-SCENARIOS.md](FAILURE-SCENARIOS.md) — failure matrix with sequence links
- [docs/adr/](adr/) — architectural decision records
- [docs/index.md](index.md) — documentation hub
- [KB-IHMS OMS-INTEGRATION.md](https://github.com/iamkaranvalecha/KB-IHMS/blob/main/docs/OMS-INTEGRATION.md) — cross-repo links only
