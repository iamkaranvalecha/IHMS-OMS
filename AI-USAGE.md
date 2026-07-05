# AI Usage Log

Mandatory transparency for every PR in checkout-orchestrator. No separate `AI-DECLARATION.md`.

## Strategy

- AI assists implementation, documentation, and test scaffolding.
- Human reviews all PRs; user owns git operations and merge decisions.
- Upstream repos (KB-IHMS, EC-OPS) are never modified by agents without explicit docs-only scope.

## Human audit checklist

- [ ] Architecture matches [DECISION-MATRIX.md](docs/DECISION-MATRIX.md)
- [ ] No upstream calls outside `src/gateway/`
- [ ] `verify.sh` output reviewed
- [ ] Living docs updated where triggers apply ([04-documentation.mdc](.cursor/rules/04-documentation.mdc))

## Verification record

| Date | Agent / session | verify.sh | Notes |
|------|-----------------|-----------|-------|
| 2026-07-04 | Cloud Agent — Phase 2 gateway | passed | 18 tests (5 unit, 5 contract, 4 component, 4 integration) |
| 2026-07-04 | Cloud Agent — Phase 3 saga | passed | 39 tests (15 unit, 6 contract, 7 component, 11 integration) |
| 2026-07-04 | Bug-finding automation — EC-OPS timeout reconciliation | passed | 42 tests (16 unit, 7 contract, 7 component, 12 integration); e2e skipped unless `STACK=1` |
| 2026-07-04 | Bug-finding automation — saga concurrency races | passed | 44 tests (18 unit, 7 contract, 7 component, 12 integration); e2e skipped unless `STACK=1` |
| 2026-07-04 | Bug-finding automation — order timeout cleanup | passed | 46 tests (20 unit, 7 contract, 7 component, 12 integration); e2e skipped unless `STACK=1` |
| 2026-07-04 | Cloud Agent — Phase 4 React UI | passed | backend verify.sh 46 tests; frontend 7 Vitest + build |
| 2026-07-04 | Bug-finding automation — frontend container API proxy | passed | `bash scripts/verify.sh`; frontend 7 Vitest + build; Docker/nginx binary unavailable for live container syntax check |
| 2026-07-05 | Cloud Agent — Phase 5 full stack E2E | passed | backend verify.sh 47 tests; `STACK=1` runs 7 e2e against mock upstream compose stack |
| 2026-07-05 | Consolidated PR #15 | passed | Supersedes #13 (frontend idempotency) + #16 (upstream rules); e2e reconcile fix |
| 2026-07-05 | Bug-finding automation — reconciliation/correlation fixes | passed | `bash scripts/verify.sh` (20 unit, 7 contract, 7 component, 15 integration); e2e skipped unless `STACK=1` |

## Session log

### 2026-07-05 — Reconciliation and correlation bug fixes

**User query:** Deep bug-finding automation for PR #15; fix only critical correctness bugs.

**Bug and impact:**
- After `POST /orders` timed out, a transient failure while querying EC-OPS `/orders` propagated as an order failure.
- The saga compensated the IHMS hold even though EC-OPS may already have created the order, risking order/hold divergence and inventory being released for a real customer order.
- Session `correlation_id` values were accepted from request bodies/headers and also used as EC-OPS reconciliation keys. Reusing a correlation ID across sessions could attach a previous order to a different checkout after a timeout.

**Human audit — rejected AI shortcuts:**
- Rejected treating a failed reconciliation lookup as "no trusted match"; a lookup that never completed cannot prove the order is absent.
- Rejected trusting caller-supplied correlation IDs for reconciliation; observability IDs are client-propagated, while reconciliation keys must be server-unique per checkout session.

**Actions:**
- Reconciliation now raises on exhausted lookup timeouts instead of returning `None`.
- The coordinator now maps reconciliation lookup failures to `CompensationIncompleteError` without releasing the hold.
- Session creation now generates a server-side UUID correlation ID and treats request-body `correlation_id` as deprecated/ignored.
- Added integration regressions for create timeout + EC-OPS list failure and caller-supplied correlation reuse; updated reconciliation docs and ADR-008.

**Verification:**
- `python3 -m pytest tests/integration/test_saga_flows.py::test_reconcile_lookup_failure_retains_hold -q` → passed.
- `python3 -m pytest tests/integration/test_health.py::test_create_session_generates_unique_correlation_id tests/integration/test_saga_flows.py::test_confirm_sends_session_correlation_to_ecops -q` → passed.
- `bash scripts/verify.sh` → passed (20 unit, 7 contract, 7 component, 15 integration; e2e skipped unless `STACK=1`).

### 2026-07-05 — Consolidate open PRs + fix e2e reconcile CI

**User query:** Analyze three open PRs, supersede one, fix e2e CI.

**Actions:**
- **Supersedes #13 and #16** — cherry-picked into #15 (single merge target)
- **E2E fix:** saga upstream calls now use `session.correlation_id` (not per-request ID) so reconcile matches mock EC-OPS `client_reference`
- Integration test `test_confirm_sends_session_correlation_to_ecops`
- PR #13: frontend confirm idempotency key persistence (`App.tsx`, `App.test.tsx`)
- PR #16: `05-upstream-evolution.mdc` + rules 01–04 updates

### 2026-07-05 — Phase 5 full stack E2E (v0.5.0)

**User query:** Continue Phase 5 after Phase 4 merge.

**Actions:**
- Wire-compatible mock IHMS + EC-OPS in `docker/mock-upstreams/`
- Fixed `docker/compose.full.yml` (healthchecks, nginx UI proxy, removed broken profiles)
- `scripts/e2e-stack.sh` for up/down/reset; `verify.sh` starts stack when `STACK=1`
- E2E tests: health, catalog, happy path, hold 409, compensate, reconcile, abandon
- CI `e2e` job enabled without `continue-on-error`
- README portfolio section; ROADMAP Phase 5 complete; version 0.5.0

### 2026-07-04 — Phase 1 scaffold (v4 plan)

**User query:** Full integration plan v4 — three-repo checkout platform scaffold.

**Actions:**
- Created module layout (`src/api`, `checkout`, `catalog`, `gateway`, `session`, `saga`)
- Living docs: DECISION-MATRIX, ARCHITECTURE, FAILURE-SCENARIOS, OBSERVABILITY, PERFORMANCE
- Sequence stubs: checkout, cancel, expiry, compensation, reconciliation
- ADR-001 through ADR-008 stubs
- Four consolidated cursor rules
- CI workflow + `scripts/verify.sh`
- Layered Docker Compose (base, dev, full)
- CLAUDE.md, AGENTS.md, ROADMAP.md

**Not done (separate repos/issues):**
- KB-IHMS `docs/OMS-INTEGRATION.md` cross-repo links
- KB-IHMS `oms-integration.mdc` update

### 2026-07-04 — Merge KB-IHMS cursor rules into 4-rule set

**User query:** Refer cursor rules from KB-IHMS repo; bring in missing or merge duplicates.

**Actions:**
- Merged KB-IHMS `git-workflow`, `github-project`, `oms-integration` → `01-workflow.mdc`
- Merged `architecture`, `hold-lifecycle`, `caching-events`, `frontend` → `02-architecture.mdc`
- Merged `testing`, `api-errors`, `http-requests` → `03-quality.mdc`
- Merged `ai-documentation` → `04-documentation.mdc`
- Updated AGENTS.md with KB-IHMS → orchestrator rule lineage table
- Excluded `dotnet-style`, `mongodb` (IHMS-specific)

### 2026-07-04 — Point project tracking to IHMS-OMS Project #5

**User query:** Update PR with project https://github.com/users/iamkaranvalecha/projects/5/views/1

**Actions:**
- Replaced all Project #4 references with Project #5 across rules, ROADMAP, README, AGENTS.md
- Updated `gh project item-list` and `--project "IHMS-OMS"` in workflow rule

### 2026-07-04 — Workflow compliance fix (Project #5)

**User query:** Why aren't you following all rules? Project details not attached.

**Human audit — rejected AI shortcuts:**
- Phase 2 started without issue-first workflow
- PR #2 opened without `Closes #N`
- Branch named `cursor/phase2-...` instead of `cursor/{issue}-...`
- No project-sync automation in repo; items not on Project #5 board

**Corrective actions:**
- Created retroactive issues [#3](https://github.com/iamkaranvalecha/IHMS-OMS/issues/3) (Phase 1), [#4](https://github.com/iamkaranvalecha/IHMS-OMS/issues/4) (Phase 2)
- Added `.github/workflows/project-sync.yml` + scripts (Project #5 field IDs)
- Added `.github/workflows/ensure-labels.yml` + `.github/labels.json`
- Added `docs/PROJECT-WORKFLOW.md`, YAML issue template
- PR #2 should include `Closes #4` (agent token lacks PR edit / project write)

**User action needed:** Configure repo secret `PROJECT_PAT`; manually add #3, #4, PR #2 to Project #5 until PAT is set; add `Closes #4` to PR #2 description.

**Update 2026-07-04:** `PROJECT_PAT` configured. Run **Sync project board** workflow (Actions → workflow_dispatch) after merging workflow files to `main`, or merge PR #2 to activate auto-sync.

### 2026-07-04 — EC-OPS timeout reconciliation bug fix

**User query:** Deep bug-finding automation for PR #6; fix only critical correctness bugs.

**Bug and impact:**
- `src/saga/coordinator.py` retried `POST /orders` after timeout with an idempotency key that frozen EC-OPS ignores, risking duplicate orders.
- `src/gateway/ecops_client.py` sent unsupported `client_ref` query params and returned the first listed order, risking session/order corruption by attaching an unrelated order.

**Human audit — rejected AI shortcuts:**
- Rejected the PR assumption that EC-OPS supports `client_reference` persistence or `Idempotency-Key` enforcement; verified against frozen EC-OPS `schemas.py`, `service.py`, and `router.py`.

**Actions:**
- Removed unsupported `client_reference` from EC-OPS create payloads.
- Reconciliation now accepts only returned orders whose `client_reference` actually matches; otherwise it compensates and surfaces the ambiguous timeout.
- Removed blind retry of `POST /orders` after timeout.
- Added unit, contract, and integration regressions for no duplicate retry and no unmatched-order reconciliation.

**Verification:**
- `python3 -m pytest tests/unit/test_saga_coordinator.py tests/contract/test_upstream_contracts.py tests/integration/test_saga_flows.py -q` → 26 passed.
- `bash scripts/verify.sh` → passed (ruff; 16 unit; 7 contract; 7 component; 12 integration; e2e skipped unless `STACK=1`).

### 2026-07-04 — Saga session concurrency bug fix

**User query:** Deep bug-finding automation for PR #6; fix only critical correctness bugs.

**Bug and impact:**
- `src/saga/coordinator.py` checked session state before upstream writes, then only locked the final in-memory mutation. Concurrent hold requests for one checkout session could create multiple IHMS holds, with the losing request failing locally after stock was already reserved.
- Concurrent confirm requests with the same idempotency key could both create EC-OPS orders before the idempotency record was stored, risking duplicate customer orders.

**Human audit — rejected AI shortcuts:**
- Rejected compensating only after a failed local mutation because confirm has no safe downstream compensation for a duplicate EC-OPS order; the state check and upstream write must be serialized together.

**Actions:**
- Exposed the per-session lock for full saga operations with upstream side effects.
- Serialized hold, confirm, and abandon flows per session before calling IHMS or EC-OPS.
- Reworked confirm finalization and compensation helpers to update state while the session lock is already held.
- Added unit regressions for concurrent hold and duplicate confirm races.

**Verification:**
- `python3 -m pytest tests/unit/test_saga_coordinator.py -q` → 13 passed.
- `bash scripts/verify.sh` → passed (ruff; 18 unit; 7 contract; 7 component; 12 integration; e2e skipped unless `STACK=1`).

### 2026-07-04 — Order timeout cleanup bug fix

**User query:** Deep bug-finding automation for PR #6; fix only critical correctness bugs.

**Bug and impact:**
- `src/saga/coordinator.py` performed a second reconciliation GET after an unreconciled `POST /orders` timeout. If that second GET failed, the exception escaped the timeout compensation branch, leaving the session `HELD` with an ambiguous EC-OPS order outcome and allowing a retry to create a duplicate order.
- Non-timeout EC-OPS transport failures escaped confirm without releasing the IHMS hold, leaking reserved inventory until expiry or manual cleanup.

**Human audit — rejected AI shortcuts:**
- Rejected adding another retry around the second reconciliation query; `_create_order_with_retry` already performs the bounded reconciliation attempts, and the unreconciled path must move directly to compensation.

**Actions:**
- Removed the duplicate reconciliation call from the outer timeout handler and made unreconciled timeouts compensate immediately.
- Added generic `GatewayError` cleanup during confirm so transport failures release the hold before surfacing the gateway error.
- Added unit regressions for unreconciled timeout cleanup and generic EC-OPS transport failure compensation.

**Verification:**
- `python3 -m pytest tests/unit/test_saga_coordinator.py -q` → 15 passed.
- `bash scripts/verify.sh` → passed (ruff; 20 unit; 7 contract; 7 component; 12 integration; e2e skipped unless `STACK=1`).

### 2026-07-04 — Phase 4 React checkout UI (Issue #10)

**User query:** Start Phase 4 after PR #6 merge.

**Actions:**
- Issue [#10](https://github.com/iamkaranvalecha/IHMS-OMS/issues/10) — React UI
- React 19 + TypeScript strict + TanStack Query + Vite
- API client with normalized types; catalog, cart, checkout, countdown, abandon confirm dialog
- Dev observability panel (correlation / trace / request IDs)
- CORS middleware on orchestrator; CI frontend job
- Version 0.4.0; ROADMAP Phase 5 current

### 2026-07-04 — Frontend container API proxy bug fix

**User query:** Deep bug-finding automation for PR #11; fix only critical correctness bugs.

**Bug and impact:**
- `frontend/Dockerfile` builds the Vite app before compose runtime environment variables are applied, so the shipped nginx image falls back to relative API paths.
- `frontend/nginx.conf` served those relative `/catalog`, `/sessions`, and `/health` paths as static SPA routes instead of proxying them to the orchestrator, leaving the Docker/compose UI unable to load catalog data or perform checkout.

**Human audit — rejected AI shortcuts:**
- Rejected relying on compose `environment: VITE_API_URL=...` for the production container because Vite only embeds `VITE_*` values at build time.

**Actions:**
- Added nginx proxy locations for `/health`, `/catalog`, and `/sessions` to forward relative API requests to the `orchestrator:8000` service on the compose network.

**Verification:**
- `cd frontend && npm install && npm test && npm run build` → 7 Vitest tests passed; production build passed.
- `bash scripts/verify.sh` → passed (ruff; 20 unit; 7 contract; 7 component; 12 integration; e2e skipped unless `STACK=1`).
- Docker, Podman, and nginx binaries were unavailable in the runner, so live container syntax validation was not performed here.

## User queries archive

| Date | Query summary |
|------|---------------|
| 2026-07-04 | IHMS-OMS project path + v4 integration plan |
| 2026-07-04 | Merge KB-IHMS cursor rules into orchestrator 4-rule set |
| 2026-07-04 | PR merged; start Phase 2 |
| 2026-07-04 | Workflow rules not followed — Project #5 not attached |
| 2026-07-04 | Deep bug-finding automation on PR #6 |
| 2026-07-04 | Deep bug-finding automation on PR #6 — saga concurrency races |
| 2026-07-04 | Deep bug-finding automation on PR #6 — order timeout cleanup |
| 2026-07-04 | Deep bug-finding automation on PR #11 — frontend container API proxy |
| 2026-07-05 | Deep bug-finding automation on PR #15 — reconciliation lookup failure and correlation collision |
