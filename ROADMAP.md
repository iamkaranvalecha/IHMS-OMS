# ROADMAP

Volatile phase tracking. Update when a phase gate passes — not in AGENTS.md.

**Project board:** [GitHub Project #4](https://github.com/users/iamkaranvalecha/projects/4)

---

## Current phase: Phase 1 — Scaffold

**Goal:** Repo structure, living docs, cursor rules, CI, verify.sh green with empty implementation.

**Active issues:** Scaffold checkout-orchestrator v4 (`integration/oms`)

**Gate checklist:**

- [x] `scripts/verify.sh` green
- [x] `docs/DECISION-MATRIX.md` reviewable
- [x] Four cursor rules in `.cursor/rules/`
- [x] `ROADMAP.md` shows Phase 1 current
- [ ] KB-IHMS doc links PR (cross-repo — separate issue)

---

## Completed

| Phase | Gate passed | Notes |
|-------|-------------|-------|
| Phase 0 | 2026-07-04 | KB-IHMS CI green; EC-OPS main CI red (Tailscale/DB — upstream frozen, not blocking scaffold) |

---

## Next

### Phase 2 — Gateway + session + catalog

- `IhmsClient`, `EcOpsClient` with observability headers
- `CatalogProvider` wired to API
- Contract + component tests

**Prerequisites:** Phase 1 gate complete

### Phase 3 — Saga + flows

- place-hold, confirm, cancel, compensation, idempotency, reconciliation
- Sequence docs finalized; integration tests per FAILURE-SCENARIOS row

### Phase 4 — React UI

- Inventory, cart, countdown, confirm/cancel
- Optional dev panel: correlation + trace IDs

### Phase 5 — Full stack + E2E

- `docker/compose.full.yml` wired to real upstream images
- E2E: happy path, hold-fail, compensate, reconciliation
- README portfolio-ready; AI-USAGE audit complete
