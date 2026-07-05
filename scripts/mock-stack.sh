#!/usr/bin/env bash
# Start the full mock checkout stack (mock IHMS + mock EC-OPS + orchestrator + UI).
#
# Resets .env to Docker-internal upstream URLs so a real-upstream .env cannot break
# `docker compose up` with "All connection attempts failed" on /catalog.
#
# Usage:
#   bash scripts/mock-stack.sh
#   bash scripts/mock-stack.sh --check   # write .env only, do not start
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --help|-h)
      echo "Usage: $0 [--check]"
      echo "  Writes mock-stack .env and runs docker compose up --build."
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

echo "==> Configuring .env for mock Docker stack"
_ensure_env_var CATALOG_SOURCE ihms
_ensure_env_var CATALOG_FALLBACK_TO_JSON false
_ensure_env_var IHMS_BASE_URL http://ihms:8080
_ensure_env_var ECOPS_BASE_URL http://ecops:8002
_ensure_env_var ECOPS_BEARER_TOKEN ""
_ensure_env_var ECOPS_MAPPING_PATH /app/catalog/ecops-mapping.json
_ensure_env_var ORCHESTRATOR_PORT 8000
_ensure_env_var UI_PORT 5180

echo "    IHMS_BASE_URL=http://ihms:8080 (mock container)"
echo "    ECOPS_BASE_URL=http://ecops:8002 (mock container)"
echo "    UI: http://localhost:5180"
echo "    API: http://localhost:8000/catalog (expect WIDGET-001 from mock IHMS)"

if [[ "$CHECK_ONLY" == "1" ]]; then
  echo "==> Mock .env written (--check)"
  exit 0
fi

echo "==> Starting full mock stack"
docker compose up --build
