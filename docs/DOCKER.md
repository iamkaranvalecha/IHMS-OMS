# Docker

Three compose stacks — one per purpose:

| Stack | Files | Command |
|-------|-------|---------|
| **Deploy** (real upstreams) | `compose.base.yml` + `compose.dev.yml` | `bash scripts/deploy-stack.sh up` |
| **Mock E2E** (CI) | `compose.base.yml` + `compose.full.yml` | `bash scripts/e2e-stack.sh up` |
| **Observability** | + `compose.observability.yml --profile obs` | `OBS_STACK=1 bash scripts/obs-stack.sh up` |

## Deploy against sibling repos

KB-IHMS ships `docker-compose.yml` (API **:5000**, frontend **:5173**). EC-OPS has **no** docker-compose — run it on the host at **:8002** with PostgreSQL (see [EC-OPS README](https://github.com/iamkaranvalecha/EC-OPS)).

```bash
# 1. KB-IHMS (from ../KB-IHMS)
docker compose up -d --build

# 2. EC-OPS (from ../EC-OPS) — local process or your deployment
uv run python scripts/setup.py && uv run python -m src.main

# 3. IHMS-OMS
cp .env.example .env
bash scripts/ecops-token.sh
bash scripts/deploy-stack.sh up
```

| Service | URL |
|---------|-----|
| Checkout UI | http://localhost:5180 |
| Orchestrator | http://localhost:8000 |
| KB-IHMS API | http://localhost:5000 |
| EC-OPS API | http://localhost:8002 |

Orchestrator reaches host upstreams via `host.docker.internal`.

### EC-OPS JWT

```bash
bash scripts/ecops-token.sh
bash scripts/deploy-stack.sh up   # reads ECOPS_BEARER_TOKEN from .env
```

`bash scripts/deploy-stack.sh down` preserves compose volumes by default. Pass `--volumes` to remove them.

## Mock stack (CI)

Unchanged — wire-compatible mocks, no external repos:

```bash
bash scripts/e2e-stack.sh up
STACK=1 bash scripts/verify.sh
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Hold fails | KB-IHMS up? `curl http://localhost:5000/health` |
| Confirm 401 | `ECOPS_BEARER_TOKEN` expired — re-run `ecops-token.sh` |
| Port clash on UI | KB-IHMS uses 5173; checkout UI uses **5180** |
