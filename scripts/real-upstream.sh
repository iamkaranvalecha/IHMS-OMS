#!/usr/bin/env bash
# Start checkout orchestrator + UI against real KB-IHMS (:5000) and EC-OPS (:8002).
#
# Prerequisites (run in sibling repos first):
#   KB-IHMS: docker compose up -d          → http://localhost:5000
#   EC-OPS:  uv run python -m src.main       → http://localhost:8002
#
# Usage:
#   ECOPS_USERNAME=admin ECOPS_PASSWORD=secret bash scripts/real-upstream.sh
#   bash scripts/real-upstream.sh --check    # verify upstreams only, do not start
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --help|-h)
      echo "Usage: $0 [--check]"
      echo "  Ensures .env is configured for real upstreams, fetches EC-OPS JWT, starts orchestrator + UI."
      exit 0
      ;;
  esac
done

_ensure_env_var() {
  local key="$1"
  local value="$2"
  touch .env
  if grep -q "^${key}=" .env 2>/dev/null; then
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s|^${key}=.*|${key}=${value}|" .env
    else
      sed -i "s|^${key}=.*|${key}=${value}|" .env
    fi
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example"
fi

_ensure_env_var CATALOG_SOURCE ihms
_ensure_env_var IHMS_BASE_URL http://host.docker.internal:5000
_ensure_env_var ECOPS_BASE_URL http://host.docker.internal:8002
_ensure_env_var ORCHESTRATOR_PORT 8000
_ensure_env_var UI_PORT 5180
_ensure_env_var ECOPS_MAPPING_PATH /app/catalog/ecops-mapping.json

echo "==> Checking KB-IHMS catalog at http://localhost:5000/api/products"
if ! curl -fsS http://localhost:5000/api/products >/dev/null; then
  echo "ERROR: KB-IHMS not reachable on http://localhost:5000 — start it first." >&2
  exit 1
fi

echo "==> Checking EC-OPS at http://localhost:8002/health"
if ! curl -fsS http://localhost:8002/health >/dev/null 2>&1; then
  echo "WARN: EC-OPS /health not found — trying root (some builds omit /health)" >&2
  if ! curl -fsS http://localhost:8002/docs >/dev/null 2>&1; then
    echo "ERROR: EC-OPS not reachable on http://localhost:8002 — start it first." >&2
    exit 1
  fi
fi

if [[ "$CHECK_ONLY" == "1" ]]; then
  echo "==> Upstreams OK (--check)"
  exit 0
fi

echo "==> Fetching EC-OPS bearer token into .env"
if [[ -n "${ECOPS_USERNAME:-}" && -n "${ECOPS_PASSWORD:-}" ]]; then
  bash scripts/ecops-token.sh
else
  echo "    Set ECOPS_USERNAME and ECOPS_PASSWORD to skip prompts, or enter them now:"
  bash scripts/ecops-token.sh
fi

echo "==> Starting orchestrator + UI (real upstream mode)"
echo "    Catalog: IHMS GET /api/products"
echo "    UI:      http://localhost:5180"
echo "    API:     http://localhost:8000/catalog"
docker compose up orchestrator ui --no-deps --build
