# ROADMAP

Volatile phase tracking. Update when a phase gate passes — not in AGENTS.md.

**Project board:** [GitHub Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1)

---

## Current phase: Complete — Phase 5 gate passed (2026-07-05)

**Goal achieved:** Full-stack Docker compose with wire-compatible mock upstreams; E2E happy path, hold-fail, compensate, reconciliation; portfolio-ready README.

---

## Completed

| Phase | Gate passed | Notes |
|-------|-------------|-------|
| Phase 0 | 2026-07-04 | KB-IHMS CI green; EC-OPS main CI red (frozen) |
| Phase 1 | 2026-07-04 | Scaffold — verify.sh, docs, 4 rules, CI |
| Phase 2 | 2026-07-04 | IhmsClient, EcOpsClient, session store, catalog API, 18 tests |
| Phase 3 | 2026-07-04 | Saga coordinator, hold/confirm/cancel, compensation, idempotency, reconciliation, 46 tests |
| Phase 4 | 2026-07-04 | React UI — catalog, cart, countdown, confirm/abandon, dev panel, Vitest |
| Phase 5 | 2026-07-05 | Mock upstreams, compose.full.yml, E2E suite, CI e2e job |

### Phase 5 deliverables

- [x] Wire-compatible mock IHMS + EC-OPS (`docker/mock-upstreams/`)
- [x] `docker/compose.full.yml` — orchestrator + UI + mocks with healthchecks
- [x] `scripts/e2e-stack.sh` — up / down / reset
- [x] E2E: health, catalog, happy path, hold 409, compensate, reconcile, abandon
- [x] CI `e2e` job runs `STACK=1 bash scripts/verify.sh`
- [x] README portfolio section; AI-USAGE audit

---

## Next

Future work (out of scope for v1 integration):

- Swap mock upstreams for published KB-IHMS / EC-OPS images in demo environments
- Persistent session store for multi-instance orchestrator
- Production observability (OpenTelemetry export)
