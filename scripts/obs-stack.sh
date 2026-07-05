#!/usr/bin/env bash
# Start stack with Prometheus (--profile obs).
set -euo pipefail
export OBS_STACK=1
exec "$(dirname "$0")/e2e-stack.sh" "$@"
