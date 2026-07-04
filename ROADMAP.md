# ROADMAP

Volatile phase tracking. Update when a phase gate passes — not in AGENTS.md.

**Project board:** [GitHub Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1)

---

## Current phase: Phase 4 — React UI

**Goal:** Inventory, cart, countdown, confirm/cancel; optional dev panel for correlation + trace IDs.

**Prerequisites:** Phase 3 gate passed (2026-07-04)

**Active issues:** `[Phase 4] React checkout UI`

---

## Completed

| Phase | Gate passed | Notes |
|-------|-------------|-------|
| Phase 0 | 2026-07-04 | KB-IHMS CI green; EC-OPS main CI red (frozen) |
| Phase 1 | 2026-07-04 | Scaffold — verify.sh, docs, 4 rules, CI |
| Phase 2 | 2026-07-04 | IhmsClient, EcOpsClient, session store, catalog API, 18 tests |
| Phase 3 | 2026-07-04 | Saga coordinator, hold/confirm/cancel, compensation, idempotency, reconciliation, 39 tests |

### Phase 3 deliverables

- [x] `SagaCoordinator` — place-hold, confirm, abandon
- [x] Compensation on EC-OPS failure (release hold → COMPENSATED)
- [x] Idempotency store for duplicate confirm
- [x] Reconciliation after POST /orders timeout (trusted client reference match only)
- [x] Per-session asyncio lock (`LockedSessionStore`)
- [x] Frozen line items on session at hold time
- [x] API: `POST /sessions/{id}/hold`, `POST /sessions/{id}/confirm`, `DELETE /sessions/{id}`
- [x] FAILURE-SCENARIOS matrix covered by unit/component/integration tests

---

## Next

### Phase 4 — React UI

- Inventory, cart, countdown, confirm/cancel
- Optional dev panel: correlation + trace IDs

### Phase 5 — Full stack + E2E

- `docker/compose.full.yml` wired to real upstream images
- E2E: happy path, hold-fail, compensate, reconciliation
- README portfolio-ready; AI-USAGE audit complete
