#!/usr/bin/env bash
# Manage IHMS-OMS Docker stack against real KB-IHMS + EC-OPS upstreams (Lane 2).
#
# Modes:
#   external (default) — upstreams already running on the host (their docker compose up)
#   bundle             — build sibling KB-IHMS + EC-OPS from disk and run everything
#
# Examples:
#   cp .env.example .env && bash scripts/ecops-token.sh   # fetch JWT into .env
#   bash scripts/upstream-stack.sh up
#   bash scripts/upstream-stack.sh up --bundle
#   OBS_STACK=1 bash scripts/upstream-stack.sh up
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

MODE="${UPSTREAM_MODE:-external}"
REMOVE_VOLUMES=0
POSITIONAL=()
while (($#)); do
  case "$1" in
    --bundle)
      MODE="bundle"
      ;;
    --external)
      MODE="external"
      ;;
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

if [[ "$MODE" == "bundle" ]]; then
  export ECOPS_DOCKERFILE="${ECOPS_DOCKERFILE:-$ROOT/docker/upstream/ecops/Dockerfile}"
fi

compose_args() {
  local args=(-f docker/compose.base.yml)
  if [[ "$MODE" == "bundle" ]]; then
    args+=(-f docker/compose.bundle.yml)
  else
    args+=(-f docker/compose.upstream.yml)
  fi
  if [[ "${OBS_STACK:-0}" == "1" ]]; then
    args+=(-f docker/compose.observability.yml --profile obs)
  fi
  printf '%s\n' "${args[@]}"
}

mapfile -t COMPOSE_ARGS < <(compose_args)
COMPOSE=(docker compose "${COMPOSE_ARGS[@]}")

ORCHESTRATOR_URL="${UPSTREAM_ORCHESTRATOR_URL:-http://localhost:${ORCHESTRATOR_PORT:-8000}}"
IHMS_URL="${UPSTREAM_IHMS_URL:-http://localhost:${IHMS_PORT:-5000}}"
ECOPS_URL="${UPSTREAM_ECOPS_URL:-http://localhost:${ECOPS_PORT:-8002}}"
UI_URL="${UPSTREAM_UI_URL:-http://localhost:${UI_PORT:-5180}}"
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

ensure_ecops_token() {
  if [[ -n "${ECOPS_BEARER_TOKEN:-}" ]]; then
    return 0
  fi
  if [[ "$MODE" == "external" ]]; then
    echo "ERROR: ECOPS_BEARER_TOKEN is required for external mode." >&2
    echo "       Register/login on EC-OPS, then run: bash scripts/ecops-token.sh" >&2
    echo "       Or set ECOPS_BEARER_TOKEN in .env" >&2
    return 1
  fi
  echo "==> ECOPS_BEARER_TOKEN not set — orchestrator order calls will fail until you set it"
  echo "    After stack is up: bash scripts/ecops-token.sh && bash scripts/upstream-stack.sh restart orchestrator"
}

cmd="${1:-up}"

case "$cmd" in
  up)
    ensure_ecops_token
    echo "==> Starting upstream stack (mode=$MODE)"
    export ECOPS_READ_TIMEOUT="${ECOPS_READ_TIMEOUT:-10}"
    export LOG_JSON="${LOG_JSON:-true}"
    "${COMPOSE[@]}" up -d --build --wait
    wait_for_url "$IHMS_URL/health" "kb-ihms"
    wait_for_url "$ECOPS_URL/health" "ec-ops"
    wait_for_url "$ORCHESTRATOR_URL/health" "orchestrator"
    wait_for_url "$ORCHESTRATOR_URL/metrics" "orchestrator-metrics"
    wait_for_url "$UI_URL/health" "checkout-ui"
    if [[ "${OBS_STACK:-0}" == "1" ]]; then
      wait_for_url "$PROMETHEUS_URL/-/healthy" "prometheus"
    fi
    echo "==> Upstream stack is up (mode=$MODE)"
    echo "    Checkout UI:  $UI_URL"
    echo "    Orchestrator: $ORCHESTRATOR_URL"
    echo "    KB-IHMS:      $IHMS_URL"
    echo "    EC-OPS:       $ECOPS_URL"
    if [[ -z "${ECOPS_BEARER_TOKEN:-}" ]]; then
      echo "    ⚠ Set ECOPS_BEARER_TOKEN then restart orchestrator for confirm flow"
    fi
    if [[ "${OBS_STACK:-0}" == "1" ]]; then
      echo "    Prometheus:   $PROMETHEUS_URL"
    fi
    ;;
  down)
    echo "==> Stopping upstream stack (mode=$MODE)"
    down_args=(down --remove-orphans)
    if [[ "$REMOVE_VOLUMES" == "1" ]]; then
      down_args+=(-v)
    fi
    "${COMPOSE[@]}" "${down_args[@]}"
    ;;
  restart)
    shift || true
    "${COMPOSE[@]}" restart "$@"
    ;;
  logs)
    service="${2:-orchestrator}"
    "${COMPOSE[@]}" logs -f "$service"
    ;;
  ps)
    "${COMPOSE[@]}" ps
    ;;
  *)
    echo "Usage: $0 [--bundle|--external] [--volumes] {up|down|restart|logs [service]|ps}" >&2
    echo "  external (default) — connect to upstreams on host ports 5000 / 8002" >&2
    echo "  --bundle           — build KB-IHMS + EC-OPS from sibling paths" >&2
    echo "  --volumes          — with down, also delete Docker volumes" >&2
    echo "  OBS_STACK=1        — enable Prometheus profile" >&2
    exit 1
    ;;
esac
