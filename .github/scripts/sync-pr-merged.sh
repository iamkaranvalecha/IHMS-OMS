#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=sync-project-fields.sh
source "$SCRIPT_DIR/sync-project-fields.sh"

PR_NUMBER="$1"
BRANCH="$2"

ISSUE_NUM="$(issue_number_from_branch "$BRANCH")"

PR_ITEM_ID="$(project_item_id_for_content "$PR_NUMBER" "PullRequest")"
set_single_select "$PR_ITEM_ID" "$FIELD_STATUS" "$STATUS_DONE"

if [[ -n "$ISSUE_NUM" ]]; then
  ISSUE_ITEM_ID="$(project_item_id_for_content "$ISSUE_NUM" "Issue")"
  set_single_select "$ISSUE_ITEM_ID" "$FIELD_STATUS" "$STATUS_DONE"
fi

echo "Marked project items Done after merge."
