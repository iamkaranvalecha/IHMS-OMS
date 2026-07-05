#!/usr/bin/env bash
# Start IHMS-OMS (orchestrator + UI) against KB-IHMS + EC-OPS on the host.
#
#   cd ../KB-IHMS && docker compose up -d
#   # EC-OPS on :8002 (see docs/DOCKER.md)
#   cp .env.example .env && bash scripts/ecops-token.sh
#   bash scripts/deploy-stack.sh up
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

REMOVE_VOLUMES=0
POSITIONAL=()
while (($#)); do
  case "$1" in
    --volumes)
      REMOVE_VOLUMES=1
      ;;
    *)
      POSITIONAL+=("$1")
      ;;
  esac
  shift
done
set -- "${POSITIONAL[@]}"

compose_args() {
  local args=(-f docker/compose.base.yml -f docker/compose.dev.yml)
  if [[ "${OBS_STACK:-0}" == "1" ]]; then
    args+=(-f docker/compose.observability.yml --profile obs)
  fi
  printf '%s\n' "${args[@]}"
}

mapfile -t COMPOSE_ARGS < <(compose_args)
COMPOSE=(docker compose "${COMPOSE_ARGS[@]}")

ORCHESTRATOR_URL="${DEPLOY_ORCHESTRATOR_URL:-http://localhost:${ORCHESTRATOR_PORT:-8000}}"
IHMS_URL="${DEPLOY_IHMS_URL:-http://localhost:${IHMS_PORT:-5000}}"
ECOPS_URL="${DEPLOY_ECOPS_URL:-http://localhost:${ECOPS_PORT:-8002}}"
UI_URL="${DEPLOY_UI_URL:-http://localhost:${UI_PORT:-5180}}"

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
  echo "ERROR: $label not ready at $url" >&2
  "${COMPOSE[@]}" ps >&2 || true
  return 1
}

cmd="${1:-up}"
case "$cmd" in
  up)
    if [[ -z "${ECOPS_BEARER_TOKEN:-}" ]]; then
      echo "ERROR: set ECOPS_BEARER_TOKEN in .env (bash scripts/ecops-token.sh)" >&2
      exit 1
    fi
    echo "==> Starting deploy stack"
    "${COMPOSE[@]}" up -d --build --wait
    wait_for_url "$IHMS_URL/health" "kb-ihms"
    wait_for_url "$ECOPS_URL/health" "ec-ops"
    wait_for_url "$ORCHESTRATOR_URL/health" "orchestrator"
    wait_for_url "$UI_URL/health" "checkout-ui"
    echo "==> Deploy stack up — UI $UI_URL | orchestrator $ORCHESTRATOR_URL"
    ;;
  down)
    down_args=(down --remove-orphans)
    if [[ "$REMOVE_VOLUMES" == "1" ]]; then
      down_args+=(-v)
    fi
    "${COMPOSE[@]}" "${down_args[@]}"
    ;;
  logs)
    "${COMPOSE[@]}" logs -f "${2:-orchestrator}"
    ;;
  *)
    echo "Usage: $0 {up|down|logs [service]} [--volumes]" >&2
    exit 1
    ;;
esac
