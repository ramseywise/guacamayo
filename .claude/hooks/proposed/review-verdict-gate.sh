#!/usr/bin/env bash
# APPLIED 2026-08-19 — installed as ~/.claude/hooks/review-verdict-gate.sh (PreToolUse).
# This proposed/ copy is retained as a historical record. Do not edit here; edit the
# installed copy at ~/.claude/hooks/review-verdict-gate.sh.
#
# review-verdict-gate.sh — block merge without /workflow-review
#
# MUST be registered under PreToolUse (Bash matcher), not PostToolUse.
# PostToolUse fires after the tool has already run; exit 2 there cannot
# un-merge anything. PreToolUse fires before, so the gate can actually block.
#
# When Ramsey applies this, copy it to ~/.claude/hooks/review-verdict-gate.sh
# alongside lib.sh. The source path below expects that layout.
#
# Fixes (GUA-117):
#   (a) Lifecycle — belongs on PreToolUse, not PostToolUse.
#   (b) Matcher — strip heredoc bodies, then match per command segment so prose
#       that merely mentions "gh pr merge" does not trip the gate.
#   (c) Report glob — tightened to *review-verdict* only; the former
#       "*review*" pattern matched any plan doc about review.
#   (d) Missing directory — if .claude/docs/plans/ does not exist the gate
#       now blocks rather than silently passing.

set -euo pipefail
# shellcheck source=/dev/null  # lib.sh sits beside this file at its install path
source "$(dirname "$0")/lib.sh"

CMD=$(claude_command)
[ -z "$CMD" ] && exit 0

# Strip heredoc bodies before matching — a gh issue create whose body merely
# *mentions* "gh pr merge" must not trip the gate (the failure that filed #117).
STRIPPED=$(strip_heredoc_bodies "$CMD")

# Match gh pr merge or gh pr review --approve only at the start of each
# command segment (after &&, ;, or |). We split on those separators and check
# each segment's leading token rather than grepping the whole string.
_matches_merge_cmd() {
  local full="$1"
  # Tokenise on &&, ;, | separators so each segment is checked independently.
  # awk is available on both GNU and BSD; no bashisms needed here.
  printf '%s\n' "$full" | awk '
    {
      n = split($0, parts, /[;&|]+/)
      for (i = 1; i <= n; i++) {
        seg = parts[i]
        gsub(/^[[:space:]]+/, "", seg)
        if (seg ~ /^gh[[:space:]]+pr[[:space:]]+(merge|review[[:space:]]+--approve)/) {
          print "match"
          exit 0
        }
      }
    }
  '
}

if [ "$(_matches_merge_cmd "$STRIPPED")" != "match" ]; then
  exit 0
fi

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

# Search for a workflow-review report newer than the last commit.
# Tightened glob: *review-verdict* only — a plan doc named
# "2026-08-15-review-attribution.md" must not satisfy this gate.
LAST_COMMIT_TS=$(git log -1 --format=%ct 2>/dev/null || echo 0)
PLANS_DIR=".claude/docs/plans"

# Defect (d): missing directory must block, not pass silently.
if [ ! -d "$PLANS_DIR" ]; then
  log_event "review_verdict_gate" "2" "plans dir absent — cannot evaluate for $BRANCH"
  block "BLOCKED: .claude/docs/plans/ does not exist. Cannot verify a /workflow-review report exists for branch '$BRANCH'. Create the directory and run /workflow-review before merging."
fi

REPORT=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  FILE_TS=$(stat -f%m "$f" 2>/dev/null || stat -c%Y "$f" 2>/dev/null || echo 0)
  if [ "$FILE_TS" -ge "$LAST_COMMIT_TS" ]; then
    REPORT="$f"
    break
  fi
done < <(find "$PLANS_DIR" -name "*review-verdict*" 2>/dev/null | sort -r)

# Gate 1: no review report newer than last commit
if [ -z "$REPORT" ]; then
  log_event "review_verdict_gate" "2" "no review report newer than last commit for $BRANCH"
  block "BLOCKED: No /workflow-review report found newer than last commit for branch '$BRANCH'. Run /workflow-review before merging."
fi

# Gate 2: review exists but has blocking verdict or findings
if grep -qE 'request_changes|insufficient_context|merge_impact:\s*blocker' "$REPORT" 2>/dev/null; then
  log_event "review_verdict_gate" "2" "blocking findings exist for $BRANCH"
  block "BLOCKED: Review report has blocking findings or non-passing verdict. Run /workflow-review to see details."
fi

log_event "review_verdict_gate" "0" "review passed for $BRANCH"
exit 0
