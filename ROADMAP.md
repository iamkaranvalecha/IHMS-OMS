# ROADMAP

Volatile phase tracking. Update when a phase gate passes — not in AGENTS.md.

**Project board:** [GitHub Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1)

---

## Current phase: v0.11 — real upstream integration + Windows DX (2026-07)

**Goal achieved:** One-click checkout against real KB-IHMS + EC-OPS; Cursor/PowerShell 7 Docker workflow; expanded workflow tests and documentation hub.

---

## Completed

| Phase | Gate passed | Notes |
|-------|-------------|-------|
| Phase 0 | 2026-07-04 | KB-IHMS CI green; EC-OPS main CI red (frozen) |
| Phase 1 | 2026-07-04 | Scaffold — verify.sh, docs, 4 rules, CI |
| Phase 2 | 2026-07-04 | IhmsClient, EcOpsClient, session store, catalog API, 18 tests |
| Phase 3 | 2026-07-04 | Saga coordinator, hold/confirm/cancel, compensation, idempotency, reconciliation |
| Phase 4 | 2026-07-04 | React UI — catalog, cart, countdown, confirm/abandon, dev panel, Vitest |
| Phase 5 | 2026-07-05 | Mock upstreams, E2E suite, CI e2e job |
| Phase 6 | 2026-07-05 | JSON logs, saga metrics, `/metrics`, observability tests |
| Phase 7 | 2026-07-05 | Single `docker-compose.yml`; v0.7.1 |
| **v0.11** | 2026-07-06 | Real upstream catalog, one-click checkout, Windows/Cursor tasks, workflow tests, [docs/index.md](docs/index.md) |

### v0.11 deliverables

- [x] `IhmsLiveCatalog` — inventory + products auto mode for real KB-IHMS
- [x] `POST /sessions/checkout` and `/place-order` — one-click Amazon-style flow
- [x] `/health/upstreams` — EC-OPS auth probe
- [x] PowerShell 7 scripts + Cursor VS Code tasks
- [x] `tests/integration/test_full_workflow.py` + e2e workflow tests
- [x] [docs/index.md](docs/index.md), [WORKFLOWS.md](docs/WORKFLOWS.md), [DESIGN-DECISIONS.md](docs/DESIGN-DECISIONS.md)

### Phase 7 deliverables

- [x] Root `docker-compose.yml` — mocks + orchestrator + UI + optional `--profile obs`
- [x] Removed layered compose files and deploy-stack scripts
- [x] README quick start matches KB-IHMS pattern

---

## Next

Future work (post v1 integration):

- OpenTelemetry SDK + OTLP export
- Scheduled Lane 2 real-upstream smoke CI job
- Persistent session store (Redis)
