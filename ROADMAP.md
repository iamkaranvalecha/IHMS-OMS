# ROADMAP

Volatile phase tracking. Update when a phase gate passes — not in AGENTS.md.

**Project board:** [GitHub Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1)

---

## Current phase: Phase 3 — Saga + flows

**Goal:** place-hold, confirm, cancel, compensation, idempotency, reconciliation path.

**Prerequisites:** Phase 2 gate passed (2026-07-04)

**Active issues:** `[Phase 3] Saga coordinator and checkout flows (UC-3..UC-7)`

---

## Completed

| Phase | Gate passed | Notes |
|-------|-------------|-------|
| Phase 0 | 2026-07-04 | KB-IHMS CI green; EC-OPS main CI red (frozen) |
| Phase 1 | 2026-07-04 | Scaffold — verify.sh, docs, 4 rules, CI |
| Phase 2 | 2026-07-04 | IhmsClient, EcOpsClient, session store, catalog API, 18 tests |

### Phase 2 deliverables

- [x] `IhmsClient` — create/get/release hold + observability headers
- [x] `EcOpsClient` — create/get/list orders + Bearer auth
- [x] `CheckoutSession` + `InMemorySessionStore`
- [x] `CheckoutService` + `/catalog`, `/sessions` API
- [x] Contract tests (respx), component tests, integration tests

---

## Next

### Phase 3 — Saga + flows

- place-hold, confirm, cancel, compensation, idempotency
- Reconciliation path for timeout scenario
- Sequence docs finalized; integration tests per FAILURE-SCENARIOS row

### Phase 4 — React UI

- Inventory, cart, countdown, confirm/cancel
- Optional dev panel: correlation + trace IDs

### Phase 5 — Full stack + E2E

- `docker/compose.full.yml` wired to real upstream images
- E2E: happy path, hold-fail, compensate, reconciliation
- README portfolio-ready; AI-USAGE audit complete
