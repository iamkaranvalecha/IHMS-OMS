#!/usr/bin/env bash
# Start mock stack in the background (detached) and wait for health.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OPEN_UI=0
for arg in "$@"; do
  case "$arg" in
    --open-ui) OPEN_UI=1 ;;
    --help|-h)
      echo "Usage: $0 [--open-ui]"
      exit 0
      ;;
  esac
done

bash scripts/mock-stack.sh --check
export ECOPS_READ_TIMEOUT="${ECOPS_READ_TIMEOUT:-10}"

echo "==> Starting mock stack (detached)"
docker compose up --build --wait -d

ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-8000}"
UI_PORT="${UI_PORT:-5180}"

wait_url() {
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
  echo "ERROR: $label not ready at $url" >&2
  return 1
}

wait_url "http://localhost:${ORCHESTRATOR_PORT}/health" "orchestrator"
wait_url "http://localhost:${UI_PORT}/health" "checkout-ui"

echo ""
echo "==> Stack ready (mock, background)"
echo "    UI:  http://localhost:${UI_PORT}"
echo "    API: http://localhost:${ORCHESTRATOR_PORT}/catalog"
echo "    Trace: http://localhost:${ORCHESTRATOR_PORT}/health/upstreams"
echo ""

if [[ "$OPEN_UI" == "1" ]]; then
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:${UI_PORT}"
  elif command -v open >/dev/null 2>&1; then
    open "http://localhost:${UI_PORT}"
  fi
fi
