# Agent Guide

Stable entry point for AI and human contributors. **Phase status lives in [ROADMAP.md](ROADMAP.md)** — not here.

## What this repo is

Checkout orchestrator (IHMS-OMS): BFF, saga, catalog mapping, and UI for integrating:

- [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS) — inventory holds (agents: no assignment code edits; API may evolve)
- [EC-OPS](https://github.com/iamkaranvalecha/EC-OPS) — order lifecycle (agents: no assignment code edits; API may evolve)

All integration code lives here. Never modify upstream assignment repos without explicit user scope. When upstream APIs change, adapt at `src/gateway/` — see [05-upstream-evolution.mdc](.cursor/rules/05-upstream-evolution.mdc).

## Read order

1. [ROADMAP.md](ROADMAP.md) — current phase and active work
2. [docs/PROJECT-WORKFLOW.md](docs/PROJECT-WORKFLOW.md) — Project #5, issues, PROJECT_PAT
3. [docs/DECISION-MATRIX.md](docs/DECISION-MATRIX.md) — 60-second architecture
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — module layout
4. Relevant [docs/sequences/](docs/sequences/) file for the flow you are changing
5. [docs/FAILURE-SCENARIOS.md](docs/FAILURE-SCENARIOS.md) — ensure your change has a matrix row
6. Applicable [docs/adr/](docs/adr/) for architectural context

## Cursor rules (mandatory)

Consolidated five-rule set (~150–250 lines each). Content merged from [KB-IHMS `.cursor/rules/`](https://github.com/iamkaranvalecha/KB-IHMS/tree/main/.cursor/rules):

| Orchestrator rule | KB-IHMS sources merged |
|-------------------|------------------------|
| [01-workflow.mdc](.cursor/rules/01-workflow.mdc) | `git-workflow`, `github-project`, `oms-integration` |
| [02-architecture.mdc](.cursor/rules/02-architecture.mdc) | `architecture`, `oms-integration`, `hold-lifecycle`, `caching-events`, `frontend` |
| [03-quality.mdc](.cursor/rules/03-quality.mdc) | `testing`, `api-errors`, `http-requests` |
| [04-documentation.mdc](.cursor/rules/04-documentation.mdc) | `ai-documentation`, `oms-integration` doc triggers |
| [05-upstream-evolution.mdc](.cursor/rules/05-upstream-evolution.mdc) | Orchestrator-specific — upstream drift, dual-lane testing |

**Not imported** (upstream-repo specific): `dotnet-style.mdc`, `mongodb.mdc`.

| Rule | Scope |
|------|-------|
| [.cursor/rules/01-workflow.mdc](.cursor/rules/01-workflow.mdc) | Issues, branches, PRs, Project #5 |
| [.cursor/rules/02-architecture.mdc](.cursor/rules/02-architecture.mdc) | Module boundaries, gateway-only upstream calls |
| [.cursor/rules/03-quality.mdc](.cursor/rules/03-quality.mdc) | Testing pyramid, saga, observability |
| [.cursor/rules/04-documentation.mdc](.cursor/rules/04-documentation.mdc) | Living docs, AI-USAGE, ROADMAP updates |
| [.cursor/rules/05-upstream-evolution.mdc](.cursor/rules/05-upstream-evolution.mdc) | Upstream API drift, contract/mock sync, real smoke |

## Project board (mandatory)

Before coding: create issue on [Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1). See [docs/PROJECT-WORKFLOW.md](docs/PROJECT-WORKFLOW.md).

Branch: `cursor/{issue-number}-description-bf51`. PR body: `Closes #N`.

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

# Docker full stack
docker compose up --build
```

## Workflow

```
AGENTS.md → ROADMAP.md → Issue → sequence + ADR
→ branch → implement (02-architecture, 03-quality)
→ verify.sh → AI-USAGE + living docs → PR
```

## Transparency

This repo uses [AI-USAGE.md](AI-USAGE.md) only. There is no `AI-DECLARATION.md` in the orchestrator (KB-IHMS keeps its own for the assignment).
