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

ECOPS_URL="${ECOPS_BASE_URL:-http://localhost:${ECOPS_PORT:-8002}}"
USERNAME="${ECOPS_USERNAME:-}"
PASSWORD="${ECOPS_PASSWORD:-}"
PRINT_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --print) PRINT_ONLY=1 ;;
    --help|-h)
      echo "Usage: $0 [--print]"
      echo "  Fetches JWT from POST ${ECOPS_URL}/auth/token"
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

echo "==> ECOPS_BEARER_TOKEN written to .env"
