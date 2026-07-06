# Docker

One file, same pattern as [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS):

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Checkout UI | http://localhost:5180 |
| Orchestrator | http://localhost:8000 |
| Mock IHMS | http://localhost:8080 |
| Mock EC-OPS | http://localhost:8012 |

Stop: `docker compose down` (add `-v` to remove volumes)

Prometheus: `docker compose --profile obs up --build` → http://localhost:9090

E2E tests: `STACK=1 bash scripts/verify.sh` (uses `scripts/e2e-stack.sh` internally)

## Windows (PowerShell / VS Code)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) on Windows.

### VS Code tasks (recommended)

Open **Terminal → Run Task…** (or `Ctrl+Shift+P` → **Tasks: Run Task**):

| Task | Purpose |
|------|---------|
| **Docker: Start full mock stack** | Mock IHMS + mock EC-OPS + orchestrator + UI (default build task) |
| **Docker: Stop stack** | `docker compose down` |
| **Real stack: Start all upstreams + orchestrator** | KB-IHMS + EC-OPS sibling repos, then orchestrator + UI |
| **EC-OPS: Fetch bearer token** | Writes `ECOPS_BEARER_TOKEN` to `.env` |
| **Health: Orchestrator upstreams** | `GET /health/upstreams` |
| **Open: Checkout UI** | Opens http://localhost:5180 |

Sibling repo paths default to `../KB-IHMS` and `../EC-OPS` (prompted when you run those tasks).

### PowerShell scripts

From the repo root in PowerShell:

```powershell
# Full mock stack (everything in Docker — no sibling repos)
.\scripts\full-stack.ps1

# Real KB-IHMS + EC-OPS on host, orchestrator + UI in Docker
$env:ECOPS_USERNAME = 'admin'
$env:ECOPS_PASSWORD = 'Password1!'
.\scripts\real-upstream.ps1

# EC-OPS JWT only
.\scripts\ecops-token.ps1

# Stop
.\scripts\stop-stack.ps1
```

CMD wrappers (double-click or `cmd.exe`): `scripts\full-stack.cmd`, `scripts\real-upstream.cmd`, etc.

### Windows troubleshooting

| Issue | Fix |
|-------|-----|
| `host.docker.internal` fails from container | Ensure Docker Desktop is running; orchestrator service already sets `extra_hosts` |
| Port already in use | Change `ORCHESTRATOR_PORT` / `UI_PORT` in `.env` |
| Script execution disabled | Use `-ExecutionPolicy Bypass` (wrappers do this) or `Set-ExecutionPolicy RemoteSigned` |
| Real upstream `.env` breaks mock stack | Run `.\scripts\mock-stack.ps1 -Check` before `docker compose up` |

## Real KB-IHMS + EC-OPS (demo / interview)

Start upstreams from their repos first, then one command:

```bash
# KB-IHMS: cd ../KB-IHMS && docker compose up -d
# EC-OPS:  cd ../EC-OPS && docker compose up -d --build   # PR #24: auto-migrate + seed admin

ECOPS_USERNAME=admin ECOPS_PASSWORD='Password1!' bash scripts/real-upstream.sh
```

**Windows:** VS Code task **Real stack: Start all upstreams + orchestrator**, or:

```powershell
$env:ECOPS_USERNAME = 'admin'; $env:ECOPS_PASSWORD = 'Password1!'
.\scripts\real-upstream.ps1
```

EC-OPS PR #24 requires migrations **0005** and **0006** (applied automatically in Docker). See [docs/EC-OPS-UPSTREAM.md](EC-OPS-UPSTREAM.md) for the full orchestrator contract.

This creates/updates `.env` (`CATALOG_SOURCE=ihms`, `CATALOG_FALLBACK_TO_JSON=false`, upstream URLs), fetches the EC-OPS JWT, and starts orchestrator + UI only.

Verify catalog shows real IHMS products:

```bash
curl -s http://localhost:8000/catalog | head
# expect MOUSE-001, KEYBOARD-002, … not WIDGET-001
```

Checkout UI: http://localhost:5180 (avoids KB-IHMS frontend on :5173).

Manual alternative:

```bash
cp .env.example .env
bash scripts/ecops-token.sh
docker compose up orchestrator ui --no-deps --build
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Bind for 0.0.0.0:5173 failed` | KB-IHMS frontend uses 5173 — checkout UI defaults to **5180** |
| `Bind for 0.0.0.0:8002 failed` | Real EC-OPS uses 8002 — mock defaults to **8012**, or use real upstream mode above |
| `Bind for 0.0.0.0:8000 failed` | Set `ORCHESTRATOR_PORT=8001` in `.env` |
