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

## Windows / Cursor dev environment

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) and **PowerShell 7** (`pwsh`) on Windows.

### PowerShell 7 setup (one-time)

Verify installed:

```powershell
pwsh -Version
```

This repo ships `.vscode/settings.json` so **Cursor and VS Code** default to PowerShell 7 for:

- Integrated terminal (`terminal.integrated.defaultProfile.windows`)
- Tasks (`terminal.integrated.automationProfile.windows` + all tasks use `pwsh`)

After `git pull`, reload the window: **`Ctrl+Shift+P` → Developer: Reload Window**.

If tasks still use Windows PowerShell 5.1, ensure `pwsh.exe` is on your PATH (default install: `C:\Program Files\PowerShell\7\`).

### Cursor / VS Code tasks (recommended)

**`Ctrl+Shift+P` → Tasks: Run Task** (same in Cursor and VS Code):

| Task | Purpose |
|------|---------|
| **Cursor: Quick start mock + open UI** | Best first run — detached stack + browser |
| **Cursor: Quick start mock stack (background)** | Default build task — stack runs while you code |
| **Cursor: Real dev environment (full)** | KB-IHMS + EC-OPS + orchestrator + health + UI |
| **Cursor: Stop stack** | `docker compose down` |
| **Health: Verify stack** | `/health/upstreams` + catalog preview |
| **EC-OPS: Fetch bearer token** | Writes `ECOPS_BEARER_TOKEN` to `.env` |
| **Docker: View orchestrator logs** | Follow orchestrator container logs |

Tasks are cross-platform: PowerShell on Windows, bash on Linux/macOS. See [.cursor/rules/06-docker-dev.mdc](../.cursor/rules/06-docker-dev.mdc) for agents.

Sibling repo paths default to `../KB-IHMS` and `../EC-OPS` (prompted when you run upstream tasks).

### PowerShell scripts

From the repo root in PowerShell:

```powershell
# Quick start (detached — recommended in Cursor)
.\scripts\dev-up.ps1 -OpenUi

# Foreground logs (debugging)
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
| Task runs Windows PowerShell 5.1 instead of 7 | Reload window after pull; confirm `pwsh -Version` works; check `.vscode/settings.json` |

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
| Place order: **Invalid or expired credentials** | Orchestrator container has stale/empty JWT — task **EC-OPS: Refresh token + restart orchestrator** or `.\scripts\refresh-ecops-token.ps1 -Username admin -Password 'Password1!'` |
| Check auth before checkout | `Invoke-RestMethod http://localhost:8000/health/upstreams` — expect `ecops.auth_ok: true` |
