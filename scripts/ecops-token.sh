#!/usr/bin/env bash
# Obtain EC-OPS JWT and write ECOPS_BEARER_TOKEN into .env (or print to stdout).
#
# Usage:
#   bash scripts/ecops-token.sh
#   ECOPS_USERNAME=admin ECOPS_PASSWORD=secret bash scripts/ecops-token.sh
#   bash scripts/ecops-token.sh --print   # stdout only, do not update .env
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

host_reachable_url() {
  local url="$1"
  case "$url" in
    http://host.docker.internal*)
      printf 'http://localhost%s\n' "${url#http://host.docker.internal}"
      ;;
    https://host.docker.internal*)
      printf 'https://localhost%s\n' "${url#https://host.docker.internal}"
      ;;
    *)
      printf '%s\n' "$url"
      ;;
  esac
}

ECOPS_URL="${ECOPS_TOKEN_URL:-}"
if [[ -z "$ECOPS_URL" ]]; then
  ECOPS_URL="$(host_reachable_url "${ECOPS_BASE_URL:-http://localhost:${ECOPS_PORT:-8002}}")"
fi
USERNAME="${ECOPS_USERNAME:-}"
PASSWORD="${ECOPS_PASSWORD:-}"
PRINT_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --print) PRINT_ONLY=1 ;;
    --help|-h)
      echo "Usage: $0 [--print]"
      echo "  Fetches JWT from POST ${ECOPS_URL}/auth/token"
      echo "  Env: ECOPS_TOKEN_URL overrides host-side token endpoint"
      echo "  Env: ECOPS_USERNAME, ECOPS_PASSWORD (prompted if unset)"
      exit 0
      ;;
  esac
done

if [[ -z "$USERNAME" ]]; then
  read -r -p "EC-OPS username: " USERNAME
fi
if [[ -z "$PASSWORD" ]]; then
  read -r -s -p "EC-OPS password: " PASSWORD
  echo
fi

response="$(curl -fsS -X POST "${ECOPS_URL}/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${USERNAME}&password=${PASSWORD}")"

token="$(python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" <<<"$response")"

if [[ "$PRINT_ONLY" == "1" ]]; then
  echo "$token"
  exit 0
fi

touch .env
if grep -q '^ECOPS_BEARER_TOKEN=' .env 2>/dev/null; then
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s|^ECOPS_BEARER_TOKEN=.*|ECOPS_BEARER_TOKEN=${token}|" .env
  else
    sed -i "s|^ECOPS_BEARER_TOKEN=.*|ECOPS_BEARER_TOKEN=${token}|" .env
  fi
else
  printf '\nECOPS_BEARER_TOKEN=%s\n' "$token" >> .env
fi

_ensure_env_var() {
  local key="$1"
  local value="$2"
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

_ensure_env_var CATALOG_SOURCE ihms
_ensure_env_var CATALOG_FALLBACK_TO_JSON false
_ensure_env_var IHMS_BASE_URL "${IHMS_BASE_URL:-http://host.docker.internal:5000}"
_ensure_env_var ECOPS_BASE_URL "${ECOPS_BASE_URL:-http://host.docker.internal:8002}"

echo "==> ECOPS_BEARER_TOKEN written to .env (CATALOG_SOURCE=ihms)"
