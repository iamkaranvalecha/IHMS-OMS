#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=sync-project-fields.sh
source "$SCRIPT_DIR/sync-project-fields.sh"

PR_URL="$1"
BRANCH="$2"
PR_NUMBER="${3:-}"

ISSUE_NUM="$(issue_number_from_branch "$BRANCH")"
if [[ -z "$ISSUE_NUM" && -n "$PR_NUMBER" ]]; then
  ISSUE_NUM="$(issue_number_from_pr "$PR_NUMBER")"
fi
LABELS=""
if [[ -n "$ISSUE_NUM" ]]; then
  LABELS="$(labels_for_issue "$ISSUE_NUM")"
fi

PR_ITEM_ID="$(add_url_to_project "$PR_URL")"
set_single_select "$PR_ITEM_ID" "$FIELD_STATUS" "$STATUS_IN_REVIEW"
apply_labels_to_item "$PR_ITEM_ID" "$LABELS"

if [[ -n "$ISSUE_NUM" ]]; then
  ISSUE_ITEM_ID="$(project_item_id_for_content "$ISSUE_NUM" "Issue")"
  set_single_select "$ISSUE_ITEM_ID" "$FIELD_STATUS" "$STATUS_IN_REVIEW"
  apply_labels_to_item "$ISSUE_ITEM_ID" "$LABELS"
fi

echo "Synced PR to IHMS-OMS Project #5 (status: In review)."
