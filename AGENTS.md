# Agent Guide

Stable entry point for AI and human contributors. **Phase status lives in [ROADMAP.md](ROADMAP.md)** — not here.

## What this repo is

Checkout orchestrator (IHMS-OMS): BFF, saga, catalog mapping, and UI for integrating:

- [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS) — inventory holds (frozen)
- [EC-OPS](https://github.com/iamkaranvalecha/EC-OPS) — order lifecycle (frozen)

All integration code lives here. Never modify upstream assignment repos.

## Read order

1. [ROADMAP.md](ROADMAP.md) — current phase and active work
2. [docs/DECISION-MATRIX.md](docs/DECISION-MATRIX.md) — 60-second architecture
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — module layout
4. Relevant [docs/sequences/](docs/sequences/) file for the flow you are changing
5. [docs/FAILURE-SCENARIOS.md](docs/FAILURE-SCENARIOS.md) — ensure your change has a matrix row
6. Applicable [docs/adr/](docs/adr/) for architectural context

## Cursor rules (mandatory)

Consolidated four-rule set (~150–250 lines each). Content merged from [KB-IHMS `.cursor/rules/`](https://github.com/iamkaranvalecha/KB-IHMS/tree/main/.cursor/rules):

| Orchestrator rule | KB-IHMS sources merged |
|-------------------|------------------------|
| [01-workflow.mdc](.cursor/rules/01-workflow.mdc) | `git-workflow`, `github-project`, `oms-integration` |
| [02-architecture.mdc](.cursor/rules/02-architecture.mdc) | `architecture`, `oms-integration`, `hold-lifecycle`, `caching-events`, `frontend` |
| [03-quality.mdc](.cursor/rules/03-quality.mdc) | `testing`, `api-errors`, `http-requests` |
| [04-documentation.mdc](.cursor/rules/04-documentation.mdc) | `ai-documentation`, `oms-integration` doc triggers |

**Not imported** (upstream-repo specific): `dotnet-style.mdc`, `mongodb.mdc`.

| Rule | Scope |
|------|-------|
| [.cursor/rules/01-workflow.mdc](.cursor/rules/01-workflow.mdc) | Issues, branches, PRs, Project #4 |
| [.cursor/rules/02-architecture.mdc](.cursor/rules/02-architecture.mdc) | Module boundaries, gateway-only upstream calls |
| [.cursor/rules/03-quality.mdc](.cursor/rules/03-quality.mdc) | Testing pyramid, saga, observability |
| [.cursor/rules/04-documentation.mdc](.cursor/rules/04-documentation.mdc) | Living docs, AI-USAGE, ROADMAP updates |

## Obligations summary

- Open a GitHub Issue before non-trivial code (`integration/oms` label).
- Branch: `cursor/{issue}-*` — never push directly to `main`.
- PR must include `Closes #N` and pass `scripts/verify.sh`.
- Update [AI-USAGE.md](AI-USAGE.md) before every PR.
- Upstream repos untouched unless explicitly scoped as docs-only cross-repo PR.

## Verification commands

```bash
# Full local gate (matches CI)
bash scripts/verify.sh

# Individual tiers
pytest tests/unit -v
pytest tests/contract -v
pytest tests/component -v
pytest tests/integration -v

# E2E (requires full stack)
STACK=1 bash scripts/verify.sh

# Docker dev stack
docker compose -f docker/compose.base.yml -f docker/compose.dev.yml up

# Docker full stack (Phase 5)
docker compose -f docker/compose.base.yml -f docker/compose.full.yml up --build
```

## Workflow

```
AGENTS.md → ROADMAP.md → Issue → sequence + ADR
→ branch → implement (02-architecture, 03-quality)
→ verify.sh → AI-USAGE + living docs → PR
```

## Transparency

This repo uses [AI-USAGE.md](AI-USAGE.md) only. There is no `AI-DECLARATION.md` in the orchestrator (KB-IHMS keeps its own for the assignment).
