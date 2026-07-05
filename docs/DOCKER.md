# Docker deployment

Three-repo layout for the distributed checkout platform. KB-IHMS and EC-OPS ship their own Docker stacks; this repo adds orchestrator + checkout UI wiring.

## Stack modes

| Mode | Compose files | When to use |
|------|---------------|-------------|
| **Mock E2E** (CI default) | `compose.base.yml` + `compose.full.yml` | PR CI, local regression without upstream repos |
| **External upstream** | `compose.base.yml` + `compose.upstream.yml` | KB-IHMS + EC-OPS already running on the host |
| **Bundled upstream** | `compose.base.yml` + `compose.bundle.yml` | All three repos cloned as siblings on one machine |
| **Dev orchestrator only** | `compose.base.yml` + `compose.dev.yml` | Orchestrator container pointing at host upstreams |

## Recommended directory layout

```
parent/
  KB-IHMS/     ← docker compose up  (API on host :5000)
  EC-OPS/      ← running on host :8002 (or built via bundle)
  IHMS-OMS/    ← this repo
```

## External upstream (deployed KB-IHMS + EC-OPS)

Start upstream repos first:

```bash
# Terminal 1 — KB-IHMS (from their repo)
cd ../KB-IHMS && docker compose up --build

# Terminal 2 — EC-OPS (from their repo, or your existing deployment)
cd ../EC-OPS && uv run python -m src.main   # or your docker setup on :8002
```

Then start IHMS-OMS against those services:

```bash
cd IHMS-OMS
cp .env.example .env
bash scripts/ecops-token.sh          # writes ECOPS_BEARER_TOKEN to .env
bash scripts/upstream-stack.sh up
```

| Service | URL |
|---------|-----|
| Checkout UI | http://localhost:5180 |
| Orchestrator | http://localhost:8000 |
| KB-IHMS (host) | http://localhost:5000 |
| EC-OPS (host) | http://localhost:8002 |

The orchestrator container reaches host upstreams via `host.docker.internal` (Linux: `extra_hosts: host-gateway`).

### EC-OPS authentication

EC-OPS requires a JWT Bearer token for `/orders`. Set `ECOPS_BEARER_TOKEN` in `.env`:

```bash
bash scripts/ecops-token.sh
# or manually:
curl -X POST http://localhost:8002/auth/token -d "username=admin&password=YOUR_PASSWORD"
```

Restart orchestrator after updating the token:

```bash
bash scripts/upstream-stack.sh restart orchestrator
```

## Bundled upstream (build siblings from disk)

Builds KB-IHMS API + EC-OPS API + orchestrator + UI on one Docker network. Does **not** start KB-IHMS frontend (avoids port 5173 clash).

```bash
KB_IHMS_PATH=../KB-IHMS ECOPS_PATH=../EC-OPS bash scripts/upstream-stack.sh up --bundle
bash scripts/ecops-token.sh
bash scripts/upstream-stack.sh restart orchestrator
```

EC-OPS is built using `docker/upstream/ecops/Dockerfile` with build context pointing at the sibling EC-OPS checkout — the assignment repo is not modified.

## Mock stack (CI / Lane 1b)

Unchanged — wire-compatible mocks for deterministic E2E:

```bash
bash scripts/e2e-stack.sh up
STACK=1 bash scripts/verify.sh
bash scripts/e2e-stack.sh down
```

## Observability overlay

Prometheus works with any stack mode:

```bash
OBS_STACK=1 bash scripts/upstream-stack.sh up
OBS_STACK=1 bash scripts/upstream-stack.sh up --bundle
bash scripts/obs-stack.sh up   # mock stack + Prometheus
```

## Environment reference

See [.env.example](../.env.example). Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `IHMS_BASE_URL` | `http://host.docker.internal:5000` | KB-IHMS API (external mode) |
| `ECOPS_BASE_URL` | `http://host.docker.internal:8002` | EC-OPS API (external mode) |
| `ECOPS_BEARER_TOKEN` | *(required external)* | JWT for EC-OPS order endpoints |
| `UI_PORT` | `5180` | Checkout UI host port |
| `KB_IHMS_PATH` | `../KB-IHMS` | Sibling path for bundle build |
| `ECOPS_PATH` | `../EC-OPS` | Sibling path for bundle build |

## Lane 2 smoke (real upstreams)

After the stack is up, exercise checkout manually via UI or curl. Record results in [AI-USAGE.md](../AI-USAGE.md).

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:5000/health
curl http://localhost:8002/health

# Full verify with mocks remains CI default:
bash scripts/verify.sh
```

Real-upstream E2E is intentionally manual — upstream data seeding and auth differ from mocks.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Orchestrator 502 on hold | KB-IHMS reachable from container: `docker compose logs orchestrator` |
| Confirm returns 401/403 | `ECOPS_BEARER_TOKEN` set and not expired (24h default) |
| UI port conflict | KB-IHMS frontend uses 5173; checkout UI defaults to **5180** |
| Bundle EC-OPS build fails | `ECOPS_PATH` points at EC-OPS repo root with `pyproject.toml` |
| Bundle IHMS build fails | `KB_IHMS_PATH` points at KB-IHMS repo root with `Dockerfile` |
