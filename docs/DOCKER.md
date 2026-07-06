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

## Real KB-IHMS + EC-OPS (demo / interview)

Start upstreams from their repos first, then one command:

```bash
# KB-IHMS: cd ../KB-IHMS && docker compose up -d
# EC-OPS:  cd ../EC-OPS && docker compose up -d --build   # PR #24: auto-migrate + seed admin

ECOPS_USERNAME=admin ECOPS_PASSWORD='Password1!' bash scripts/real-upstream.sh
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
