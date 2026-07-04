#!/usr/bin/env bash
# Local verification — mirrors CI. E2E runs when STACK=1.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> ruff"
python3 -m ruff check src tests

echo "==> unit"
python3 -m pytest tests/unit -v --tb=short

echo "==> contract"
python3 -m pytest tests/contract -v --tb=short

echo "==> component"
python3 -m pytest tests/component -v --tb=short

echo "==> integration"
python3 -m pytest tests/integration -v --tb=short

if [[ "${STACK:-0}" == "1" ]]; then
  echo "==> e2e (STACK=1)"
  python3 -m pytest tests/e2e -v --tb=short -m e2e
else
  echo "==> e2e skipped (set STACK=1 to run)"
fi

echo "==> verify.sh passed"
