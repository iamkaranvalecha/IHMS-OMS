#!/usr/bin/env bash
# Start the full IHMS-OMS Docker stack (mock IHMS + mock EC-OPS + orchestrator + UI).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash scripts/mock-stack.sh --check
export ECOPS_READ_TIMEOUT="${ECOPS_READ_TIMEOUT:-10}"
docker compose up --build --wait

echo ""
echo "==> Stack ready"
echo "    UI:  http://localhost:${UI_PORT:-5180}"
echo "    API: http://localhost:${ORCHESTRATOR_PORT:-8000}/catalog"
echo "    Trace: curl http://localhost:${ORCHESTRATOR_PORT:-8000}/health/upstreams"
echo ""
echo "Place order: open UI, add to cart, click Place order"
