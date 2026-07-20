#!/usr/bin/env bash
# dream-ledger-gate.sh — PostToolUse hook for Edit/Write on .sounding/growth.md
# Blocks if growth.md entries were cleared without corresponding growth-log.md rows.
#
# Logic: after an edit to growth.md, count remaining dated entries (YYYY-MM-DD lines).
# If count dropped to 0 (a clear), verify growth-log.md gained rows today.
# Exit 2 = block (missing ledger rows). Exit 0 = pass.
#
# Bypass: GUACAMAYO_SKIP_LEDGER_GATE=1

set -euo pipefail

# Bypass valve
[ "${GUACAMAYO_SKIP_LEDGER_GATE:-0}" = "1" ] && exit 0

# Only fire on .sounding/growth.md edits
file_path=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // empty')
[ -z "$file_path" ] && exit 0
case "$file_path" in
  */.sounding/growth.md|*.sounding/growth.md) ;;
  *) exit 0 ;;
esac

# Resolve repo root from the file path
repo_root=$(echo "$file_path" | sed 's|/.sounding/growth.md$||')
growth="$repo_root/.sounding/growth.md"
ledger="$repo_root/.sounding/growth-log.md"

# Count dated entries remaining in growth.md (lines matching YYYY-MM-DD [tag])
remaining=$(grep -cE '^[0-9]{4}-[0-9]{2}-[0-9]{2} \[' "$growth" 2>/dev/null || true)
remaining=${remaining:-0}
remaining=$((remaining + 0))

# If entries remain, this is an append (/grow) or partial edit — not a clear. Pass.
[ "$remaining" -gt 0 ] && exit 0

# growth.md was cleared (0 dated entries). Check ledger exists and has today's rows.
if [ ! -f "$ledger" ]; then
  echo "Blocked: growth.md cleared but growth-log.md does not exist." >&2
  echo "Write growth-log.md rows first (dream Phase 7c-bis)." >&2
  exit 2
fi

today=$(date '+%Y-%m-%d')
today_rows=$(grep -cE "^\| $today" "$ledger" 2>/dev/null || true)
today_rows=${today_rows:-0}
today_rows=$((today_rows + 0))

if [ "$today_rows" -lt 1 ]; then
  echo "Blocked: growth.md cleared but growth-log.md has 0 rows dated $today." >&2
  echo "Write growth-log.md rows first (dream Phase 7c-bis)." >&2
  exit 2
fi

exit 0
