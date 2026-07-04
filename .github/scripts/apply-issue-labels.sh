#!/usr/bin/env bash
# Apply priority, size, and phase labels after creating an issue from the integration template.
# Usage: apply-issue-labels.sh <issue-number> <priority:p0|p1|p2> <size:xs|s|m|l|xl> <phase:1|2|3|4|5>
set -euo pipefail

ISSUE_NUMBER="$1"
PRIORITY="$2"
SIZE="$3"
PHASE="$4"

REPO="${GITHUB_REPOSITORY:-iamkaranvalecha/IHMS-OMS}"

gh issue edit "$ISSUE_NUMBER" --repo "$REPO" \
  --add-label "integration/oms,priority/$PRIORITY,size/$SIZE,phase-$PHASE"
