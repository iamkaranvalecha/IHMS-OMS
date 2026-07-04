# ROADMAP

Volatile phase tracking. Update when a phase gate passes — not in AGENTS.md.

**Project board:** [GitHub Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1)

---

## Current phase: Phase 5 — Full stack + E2E

**Goal:** `docker/compose.full.yml` wired to real upstream images; E2E happy path, hold-fail, compensate, reconciliation; portfolio-ready README.

**Prerequisites:** Phase 4 gate passed (2026-07-04)

**Active issues:** `[Phase 5] Full stack E2E`

---

## Completed

| Phase | Gate passed | Notes |
|-------|-------------|-------|
| Phase 0 | 2026-07-04 | KB-IHMS CI green; EC-OPS main CI red (frozen) |
| Phase 1 | 2026-07-04 | Scaffold — verify.sh, docs, 4 rules, CI |
| Phase 2 | 2026-07-04 | IhmsClient, EcOpsClient, session store, catalog API, 18 tests |
| Phase 3 | 2026-07-04 | Saga coordinator, hold/confirm/cancel, compensation, idempotency, reconciliation, 46 tests |
| Phase 4 | 2026-07-04 | React UI — catalog, cart, countdown, confirm/abandon, dev panel, Vitest |

### Phase 4 deliverables

- [x] TypeScript strict + TanStack Query
- [x] API client with normalized types (`frontend/src/api/`)
- [x] Catalog browse + cart + checkout flow
- [x] Hold countdown; confirm disabled when expired
- [x] Abandon confirmation dialog
- [x] Dev observability panel (correlation / trace / request IDs)
- [x] CORS on orchestrator for local UI dev
- [x] CI frontend job (`npm test`, `npm run build`)

---

## Next

### Phase 5 — Full stack + E2E

- `docker/compose.full.yml` wired to real upstream images
- E2E: happy path, hold-fail, compensate, reconciliation
- README portfolio-ready; AI-USAGE audit complete
