# React Checkout UI

Orchestrator-facing checkout UI (Phase 4). Calls **orchestrator API only** — never KB-IHMS or EC-OPS directly.

## Stack

- React 19 + TypeScript (strict)
- Vite 6
- TanStack Query
- Vitest

## Development

```bash
# Terminal 1 — API
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8000

# Terminal 2 — UI
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Vite dev server |
| `npm test` | Vitest unit tests |
| `npm run build` | Production build |

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | (empty = same origin) | Orchestrator base URL |
