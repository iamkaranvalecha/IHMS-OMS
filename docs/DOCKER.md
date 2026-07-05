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

## Real KB-IHMS + EC-OPS (optional)

Start upstreams from their repos first, then run orchestrator + UI only:

```bash
# KB-IHMS: cd ../KB-IHMS && docker compose up -d
# EC-OPS:  cd ../EC-OPS && uv run python -m src.main

cp .env.example .env
bash scripts/ecops-token.sh

docker compose up orchestrator ui --no-deps --build
```

With the example env, the checkout UI is exposed at http://localhost:5180 to avoid
KB-IHMS' frontend on http://localhost:5173.

`ecops-token.sh` maps `host.docker.internal` to `localhost` when fetching the JWT from your host.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Bind for 0.0.0.0:5173 failed` | KB-IHMS frontend uses 5173 — checkout UI defaults to **5180** |
| `Bind for 0.0.0.0:8002 failed` | Real EC-OPS uses 8002 — mock defaults to **8012**, or use real upstream mode above |
| `Bind for 0.0.0.0:8000 failed` | Set `ORCHESTRATOR_PORT=8001` in `.env` |
