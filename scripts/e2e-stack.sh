#!/usr/bin/env bash
# Manage the Docker stack for E2E tests (wraps docker compose).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# docker compose reads .env automatically. Force mock-stack defaults here so a
# real-upstream .env cannot redirect E2E traffic away from the mock containers.
export IHMS_BASE_URL="http://ihms:8080"
export ECOPS_BASE_URL="http://ecops:8002"
export ECOPS_BEARER_TOKEN=""
export ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-8000}"
export IHMS_PORT="${IHMS_PORT:-8080}"
export ECOPS_PORT="${ECOPS_PORT:-8002}"
export UI_PORT="${UI_PORT:-5173}"

COMPOSE=(docker compose)
if [[ "${OBS_STACK:-0}" == "1" ]]; then
  COMPOSE+=(--profile obs)
fi

ORCHESTRATOR_URL="${E2E_ORCHESTRATOR_URL:-http://localhost:${ORCHESTRATOR_PORT:-8000}}"
IHMS_URL="${E2E_IHMS_ADMIN_URL:-http://localhost:${IHMS_PORT:-8080}}"
ECOPS_URL="${E2E_ECOPS_ADMIN_URL:-http://localhost:${ECOPS_PORT:-8002}}"
UI_URL="${E2E_UI_URL:-http://localhost:${UI_PORT:-5173}}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:${PROMETHEUS_PORT:-9090}}"

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"
  local delay="${4:-2}"
  local i=1
  while (( i <= attempts )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "==> $label ready at $url"
      return 0
    fi
    sleep "$delay"
    ((i++))
  done
  echo "ERROR: $label not ready at $url after $((attempts * delay))s" >&2
  "${COMPOSE[@]}" ps >&2 || true
  "${COMPOSE[@]}" logs --tail=50 >&2 || true
  return 1
}

cmd="${1:-up}"

case "$cmd" in
  up)
    echo "==> Starting stack (docker compose up)"
    export ECOPS_READ_TIMEOUT="${ECOPS_READ_TIMEOUT:-2}"
    export LOG_JSON="${LOG_JSON:-true}"
    "${COMPOSE[@]}" up -d --build --wait
    wait_for_url "$ORCHESTRATOR_URL/health" "orchestrator"
    wait_for_url "$ORCHESTRATOR_URL/metrics" "orchestrator-metrics"
    wait_for_url "$IHMS_URL/health" "mock-ihms"
    wait_for_url "$ECOPS_URL/health" "mock-ecops"
    wait_for_url "$UI_URL/health" "ui"
    if [[ "${OBS_STACK:-0}" == "1" ]]; then
      wait_for_url "$PROMETHEUS_URL/-/healthy" "prometheus"
    fi
    echo "==> Stack is up"
    if [[ "${OBS_STACK:-0}" == "1" ]]; then
      echo "    Prometheus UI: $PROMETHEUS_URL"
    fi
    ;;
  down)
    echo "==> Stopping stack"
    "${COMPOSE[@]}" down -v --remove-orphans
    ;;
  reset)
    curl -fsS -X POST "$IHMS_URL/_test/reset" >/dev/null
    curl -fsS -X POST "$ECOPS_URL/_test/reset" >/dev/null
    ;;
  logs)
    service="${2:-orchestrator}"
    "${COMPOSE[@]}" logs -f "$service"
    ;;
  *)
    echo "Usage: $0 {up|down|reset|logs [service]}" >&2
    echo "  OBS_STACK=1 enables Prometheus (--profile obs)" >&2
    exit 1
    ;;
esac
