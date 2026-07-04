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

## Session log

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

## User queries archive

| Date | Query summary |
|------|---------------|
| 2026-07-04 | IHMS-OMS project path + v4 integration plan |
| 2026-07-04 | Merge KB-IHMS cursor rules into orchestrator 4-rule set |
| 2026-07-04 | PR merged; start Phase 2 |
| 2026-07-04 | Workflow rules not followed — Project #5 not attached |
