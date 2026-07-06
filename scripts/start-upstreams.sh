#!/usr/bin/env bash
# Start KB-IHMS and EC-OPS sibling repos in Docker and wait for health.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

KB_IHMS_PATH="${KB_IHMS_PATH:-../KB-IHMS}"
EC_OPS_PATH="${EC_OPS_PATH:-../EC-OPS}"

start_repo() {
  local path="$1"
  local name="$2"
  local url="$3"
  if [[ ! -d "$path" ]]; then
    echo "ERROR: $name repo not found at $path — clone it as a sibling folder first." >&2
    exit 1
  fi
  echo "==> Starting $name at $url"
  (cd "$path" && docker compose up -d --build)
}

wait_ihms() {
  for path in /api/products /api/inventory; do
    if curl -fsS "http://localhost:5000${path}" >/dev/null 2>&1; then
      echo "==> KB-IHMS ready at http://localhost:5000${path}"
      return 0
    fi
  done
  echo "ERROR: KB-IHMS not reachable on http://localhost:5000" >&2
  exit 1
}

wait_ecops() {
  for url in http://localhost:8002/health http://localhost:8002/docs; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "==> EC-OPS ready at $url"
      return 0
    fi
  done
  echo "ERROR: EC-OPS not reachable on http://localhost:8002" >&2
  exit 1
}

start_repo "$KB_IHMS_PATH" "KB-IHMS" "http://localhost:5000"
start_repo "$EC_OPS_PATH" "EC-OPS" "http://localhost:8002"
wait_ihms
wait_ecops
echo "==> Real upstreams ready"
