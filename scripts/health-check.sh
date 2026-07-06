#!/usr/bin/env bash
# Verify orchestrator + UI health and print upstream diagnostics.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-8000}"
UI_PORT="${UI_PORT:-5180}"

curl -fsS "http://localhost:${ORCHESTRATOR_PORT}/health" >/dev/null
curl -fsS "http://localhost:${UI_PORT}/health" >/dev/null

echo "==> Upstreams"
curl -fsS "http://localhost:${ORCHESTRATOR_PORT}/health/upstreams" | python3 -m json.tool

echo ""
echo "==> Catalog (first item)"
curl -fsS "http://localhost:${ORCHESTRATOR_PORT}/catalog" | python3 -c "import json,sys; d=json.load(sys.stdin); items=d.get('items') or [d]; print(json.dumps(items[0] if items else d, indent=2))"
