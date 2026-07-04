#!/usr/bin/env bash
# Shared helpers for syncing GitHub Project #5 (IHMS-OMS) fields from labels and branch names.
set -euo pipefail

export OWNER="iamkaranvalecha"
export REPO="IHMS-OMS"
export PROJECT_NUMBER=5
export PROJECT_ID="PVT_kwHOAKhJ184BcdYO"

export FIELD_STATUS="PVTSSF_lAHOAKhJ184BcdYOzhXGCAQ"
export FIELD_PRIORITY="PVTSSF_lAHOAKhJ184BcdYOzhXGCDA"
export FIELD_SIZE="PVTSSF_lAHOAKhJ184BcdYOzhXGCDE"

export STATUS_BACKLOG="f75ad846"
export STATUS_READY="e18bf179"
export STATUS_IN_PROGRESS="47fc9ee4"
export STATUS_IN_REVIEW="aba860b9"
export STATUS_DONE="98236657"

export PRIORITY_P0="79628723"
export PRIORITY_P1="0a877460"
export PRIORITY_P2="da944a9c"

export SIZE_XS="911790be"
export SIZE_S="b277fb01"
export SIZE_M="86db8eb3"
export SIZE_L="853c8207"
export SIZE_XL="2d0801e2"

issue_number_from_branch() {
  local branch="$1"
  if [[ "$branch" =~ ^cursor/([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]}"
  fi
}

labels_for_issue() {
  local issue_number="$1"
  gh issue view "$issue_number" --repo "$OWNER/$REPO" --json labels -q '.labels[].name' 2>/dev/null || true
}

priority_option_from_labels() {
  local labels="$1"
  if echo "$labels" | grep -qx 'priority/p0'; then echo "$PRIORITY_P0"
  elif echo "$labels" | grep -qx 'priority/p1'; then echo "$PRIORITY_P1"
  elif echo "$labels" | grep -qx 'priority/p2'; then echo "$PRIORITY_P2"
  else echo "$PRIORITY_P1"
  fi
}

size_option_from_labels() {
  local labels="$1"
  if echo "$labels" | grep -qx 'size/xs'; then echo "$SIZE_XS"
  elif echo "$labels" | grep -qx 'size/s'; then echo "$SIZE_S"
  elif echo "$labels" | grep -qx 'size/m'; then echo "$SIZE_M"
  elif echo "$labels" | grep -qx 'size/l'; then echo "$SIZE_L"
  elif echo "$labels" | grep -qx 'size/xl'; then echo "$SIZE_XL"
  fi
}

project_item_id_for_content() {
  local content_number="$1"
  local content_type="$2"
  gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --format json --limit 200 \
    | jq -r --arg num "$content_number" --arg type "$content_type" \
      '.items[] | select(.content.number == ($num | tonumber) and .content.type == $type) | .id' \
    | head -n 1
}

set_single_select() {
  local item_id="$1"
  local field_id="$2"
  local option_id="$3"
  [[ -z "$item_id" || -z "$option_id" ]] && return 0
  gh project item-edit \
    --id "$item_id" \
    --project-id "$PROJECT_ID" \
    --field-id "$field_id" \
    --single-select-option-id "$option_id"
}

apply_labels_to_item() {
  local item_id="$1"
  local labels="$2"
  set_single_select "$item_id" "$FIELD_PRIORITY" "$(priority_option_from_labels "$labels")"
  local size_option
  size_option="$(size_option_from_labels "$labels")"
  if [[ -n "$size_option" ]]; then
    set_single_select "$item_id" "$FIELD_SIZE" "$size_option"
  fi
}

add_url_to_project() {
  local url="$1"
  gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$url" --format json -q '.id'
}
