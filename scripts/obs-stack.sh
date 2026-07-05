#!/usr/bin/env bash
# Start full stack with Prometheus scraping orchestrator /metrics.
set -euo pipefail

export OBS_STACK=1
exec "$(dirname "$0")/e2e-stack.sh" "$@"
