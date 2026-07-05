# CLAUDE.md

Slim agent entry point. Details live in linked docs — keep this file ≤150 lines.

## Mission

Build the **checkout orchestrator** ([IHMS-OMS](https://github.com/iamkaranvalecha/IHMS-OMS)) — a FastAPI BFF and saga layer that integrates [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS) inventory holds with [EC-OPS](https://github.com/iamkaranvalecha/EC-OPS) order lifecycle. Agents do not edit upstream assignment code; upstream APIs may evolve — adapt at `src/gateway/`. All integration, catalog mapping, observability, and UI live in this repo.

## Commands

```bash
pip install -e ".[dev]"          # install
bash scripts/verify.sh           # full gate (ruff + all test tiers)
pytest tests/unit -v             # unit only
STACK=1 bash scripts/verify.sh   # include e2e

docker compose up --build
```

## Read order

1. [AGENTS.md](AGENTS.md)
2. [ROADMAP.md](ROADMAP.md) — **current phase**
3. [docs/DECISION-MATRIX.md](docs/DECISION-MATRIX.md)
4. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Quality gates

- `scripts/verify.sh` must pass before PR.
- See [.cursor/rules/03-quality.mdc](.cursor/rules/03-quality.mdc) for testing pyramid and saga rules.
- See [.cursor/rules/05-upstream-evolution.mdc](.cursor/rules/05-upstream-evolution.mdc) when gateway, contract tests, or mocks change.

## Never do

- Modify KB-IHMS or EC-OPS assignment code.
- Call IHMS or EC-OPS from UI or outside `src/gateway/`.
- Skip a [FAILURE-SCENARIOS.md](docs/FAILURE-SCENARIOS.md) row when implementing a flow.
- Add `AI-DECLARATION.md` to this repo.
- Put phase status in AGENTS.md (use ROADMAP.md).

## Always do

- Route upstream HTTP only through `src/gateway/`.
- Update gateway + contract tests + mock upstreams together when wire format changes ([05-upstream-evolution.mdc](.cursor/rules/05-upstream-evolution.mdc)).
- Update [AI-USAGE.md](AI-USAGE.md) before every PR.
- Link/update [docs/sequences/](docs/sequences/) when checkout flows change.
- Forward Request, Correlation, and Trace IDs per [OBSERVABILITY.md](docs/OBSERVABILITY.md).
- Open Issue + branch `cursor/{issue}-*` per [01-workflow.mdc](.cursor/rules/01-workflow.mdc).

## Module map

```
src/api → src/checkout → src/saga + session + catalog → src/gateway
```

## Key docs

| Doc | Purpose |
|-----|---------|
| [FAILURE-SCENARIOS.md](docs/FAILURE-SCENARIOS.md) | Failure matrix |
| [PERFORMANCE.md](docs/PERFORMANCE.md) | Timeouts, retries |
| [docs/adr/](docs/adr/) | ADRs |
| [AI-USAGE.md](AI-USAGE.md) | Transparency log |
