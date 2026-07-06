#!/usr/bin/env bash
# Refresh EC-OPS JWT and recreate orchestrator so the new token is injected.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ECOPS_USERNAME="${ECOPS_USERNAME:-}"
ECOPS_PASSWORD="${ECOPS_PASSWORD:-}"

for arg in "$@"; do
  case "$arg" in
    --help|-h)
      echo "Usage: $0"
      echo "  Env: ECOPS_USERNAME, ECOPS_PASSWORD"
      exit 0
      ;;
  esac
done

if [[ -n "$ECOPS_USERNAME" && -n "$ECOPS_PASSWORD" ]]; then
  ECOPS_USERNAME="$ECOPS_USERNAME" ECOPS_PASSWORD="$ECOPS_PASSWORD" bash scripts/ecops-token.sh
else
  bash scripts/ecops-token.sh
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ -z "${ECOPS_BEARER_TOKEN:-}" ]]; then
  echo "ERROR: ECOPS_BEARER_TOKEN is empty after token fetch" >&2
  exit 1
fi

echo "==> ECOPS_BEARER_TOKEN loaded (${#ECOPS_BEARER_TOKEN} chars)"
docker compose up orchestrator ui --no-deps --build --force-recreate -d --wait
bash scripts/health-check.sh

echo "==> Token refreshed — verify auth_ok in /health/upstreams"
