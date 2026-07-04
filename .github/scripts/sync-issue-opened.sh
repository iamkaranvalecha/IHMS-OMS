#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=sync-project-fields.sh
source "$SCRIPT_DIR/sync-project-fields.sh"

ISSUE_NUMBER="$1"

BODY="$(gh issue view "$ISSUE_NUMBER" --repo "$OWNER/$REPO" --json body -q '.body' 2>/dev/null || echo "")"
LABELS="$(labels_for_issue "$ISSUE_NUMBER")"

priority_label() {
  local body="$1"
  if echo "$body" | grep -Eiq 'P0[^0-9]|priority.*p0'; then echo "priority/p0"
  elif echo "$body" | grep -Eiq 'P2[^0-9]|priority.*p2'; then echo "priority/p2"
  else echo "priority/p1"
  fi
}

size_label() {
  local body="$1"
  if echo "$body" | grep -Eiq '\bXS\b'; then echo "size/xs"
  elif echo "$body" | grep -Eiq '\bS\b'; then echo "size/s"
  elif echo "$body" | grep -Eiq '\bM\b'; then echo "size/m"
  elif echo "$body" | grep -Eiq '\bL\b'; then echo "size/l"
  elif echo "$body" | grep -Eiq '\bXL\b'; then echo "size/xl"
  fi
}

phase_label() {
  local body="$1"
  local title
  title="$(gh issue view "$ISSUE_NUMBER" --repo "$OWNER/$REPO" --json title -q '.title' 2>/dev/null || echo "")"
  local text="$title $body"
  if echo "$text" | grep -Eiq 'phase 1|\[phase 1\]|scaffold'; then echo "phase-1"
  elif echo "$text" | grep -Eiq 'phase 2|\[phase 2\]|gateway'; then echo "phase-2"
  elif echo "$text" | grep -Eiq 'phase 3|\[phase 3\]|saga'; then echo "phase-3"
  elif echo "$text" | grep -Eiq 'phase 4|\[phase 4\]|ui|frontend'; then echo "phase-4"
  elif echo "$text" | grep -Eiq 'phase 5|\[phase 5\]|e2e|compose'; then echo "phase-5"
  fi
}

NEW_LABELS=("integration/oms")
if ! echo "$LABELS" | grep -q '^priority/'; then
  NEW_LABELS+=("$(priority_label "$BODY")")
fi
if ! echo "$LABELS" | grep -q '^size/'; then
  size="$(size_label "$BODY")"
  [[ -n "$size" ]] && NEW_LABELS+=("$size")
fi
if ! echo "$LABELS" | grep -q '^phase-'; then
  phase="$(phase_label "$BODY")"
  [[ -n "$phase" ]] && NEW_LABELS+=("$phase")
fi

if ((${#NEW_LABELS[@]} > 0)); then
  gh issue edit "$ISSUE_NUMBER" --repo "$OWNER/$REPO" --add-label "$(IFS=,; echo "${NEW_LABELS[*]}")"
  LABELS="$(labels_for_issue "$ISSUE_NUMBER")"
fi

ITEM_ID="$(project_item_id_for_content "$ISSUE_NUMBER" "Issue")"
if [[ -z "$ITEM_ID" ]]; then
  ISSUE_URL="https://github.com/$OWNER/$REPO/issues/$ISSUE_NUMBER"
  ITEM_ID="$(add_url_to_project "$ISSUE_URL")"
fi

apply_labels_to_item "$ITEM_ID" "$LABELS"
set_single_select "$ITEM_ID" "$FIELD_STATUS" "$STATUS_BACKLOG"

echo "Synced issue #$ISSUE_NUMBER to Project #5 (status: Backlog)."
