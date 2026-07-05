# Docker

One file, same pattern as [KB-IHMS](https://github.com/iamkaranvalecha/KB-IHMS):

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Checkout UI | http://localhost:5173 |
| Orchestrator | http://localhost:8000 |
| Mock IHMS | http://localhost:8080 |
| Mock EC-OPS | http://localhost:8002 |

Stop: `docker compose down` (add `-v` to remove volumes)

Prometheus: `docker compose --profile obs up --build` → http://localhost:9090

E2E tests: `STACK=1 bash scripts/verify.sh` (uses `scripts/e2e-stack.sh` internally)

## Real KB-IHMS + EC-OPS (optional)

Start upstreams from their repos first, then run orchestrator + UI only:

```bash
# KB-IHMS: cd ../KB-IHMS && docker compose up -d
# EC-OPS:  cd ../EC-OPS && uv run python -m src.main

cp .env.example .env
# Edit .env — set IHMS_BASE_URL, ECOPS_BASE_URL, ECOPS_BEARER_TOKEN

docker compose up orchestrator ui --no-deps --build
```

Get EC-OPS JWT: `curl -X POST http://localhost:8002/auth/token -d "username=USER&password=PASS"`
