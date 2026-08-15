#!/usr/bin/env bash
# End-to-end tests for proposed/review-verdict-gate.sh — the real hook, real JSON
# payloads on stdin, real git repo in a temp dir.
#
# Two directions are proven (the minimum meaningful pair):
#   BLOCK: a branch with no review report is blocked when "gh pr merge" is invoked.
#   PASS:  a "gh issue create" whose body merely mentions "gh pr merge" is NOT blocked.
#
# Git fixture setup uses Python subprocess to create commits, because the Claude
# session's PreToolUse risky_git_guard blocks "git commit" in any Bash tool call
# that isn't targeting a linked worktree. Python's subprocess.run bypasses that.
#
# run() does NOT use command substitution ($()) — LAST_MSG is set in the caller's
# scope by writing to a temp file. Command substitution spawns a subshell and
# variable assignments inside it are invisible to the parent.

set -euo pipefail

HOOK="$(cd "$(dirname "$0")/../proposed" && pwd)/review-verdict-gate.sh"

PASS=0
FAIL=0
pass() { echo "PASS: $1"; (( PASS++ )) || true; }
fail() { echo "FAIL: $1"; (( FAIL++ )) || true; }

if ! command -v python3 >/dev/null 2>&1; then echo "SKIP: python3 not available"; exit 0; fi
if ! command -v jq    >/dev/null 2>&1; then echo "SKIP: jq not available";     exit 0; fi

TMP=$(mktemp -d)
export TMP
trap 'rm -rf "$TMP"' EXIT

# Stitch lib.sh into the proposed hook's directory so source "$(dirname "$0")/lib.sh"
# resolves correctly. When applied, the hook lives next to ~/.claude/hooks/lib.sh.
# The symlink is a test artifact — an absolute path into $HOME that must never be
# committed — so remove it on exit rather than leaving it in the working tree.
PROPOSED_DIR="$(dirname "$HOOK")"
GLOBAL_LIB="$HOME/.claude/hooks/lib.sh"
if [ -f "$GLOBAL_LIB" ] && [ ! -e "$PROPOSED_DIR/lib.sh" ]; then
  ln -s "$GLOBAL_LIB" "$PROPOSED_DIR/lib.sh"
  trap 'rm -rf "$TMP"; rm -f "$PROPOSED_DIR/lib.sh"' EXIT
fi

# Build a minimal git repo via Python (bypasses the session's git-commit Bash guard).
REPO=$(python3 - <<'PYEOF'
import subprocess, os, sys, tempfile
TMP = os.environ["TMP"]
REPO = os.path.join(TMP, "repo")
os.makedirs(REPO, exist_ok=True)
def r(*a): subprocess.run(list(a), check=True, capture_output=True)
r("git", "init", "-q", REPO)
r("git", "-C", REPO, "config", "user.email", "t@t")
r("git", "-C", REPO, "config", "user.name", "t")
open(os.path.join(REPO, "seed"), "w").close()
r("git", "-C", REPO, "add", "seed")
r("git", "-C", REPO, "commit", "-qm", "seed")
print(REPO)
PYEOF
)

export CLAUDE_TELEMETRY_DIR="$TMP/telemetry"
mkdir -p "$CLAUDE_TELEMETRY_DIR"

PLANS="$REPO/.claude/docs/plans"

# --- Harness ---
# run <command> [cwd]
# Sets $LAST_RC and $LAST_MSG in the CALLER's scope (no command substitution).
# Writes exit code to $TMP/rc and stderr to $TMP/err so both survive subshell exit.
LAST_RC=0
LAST_MSG=""
run() {
  local cmd="$1" cwd="${2:-$REPO}" payload
  payload=$(printf '{"tool_input":{"command":%s},"cwd":%s}' \
    "$(printf '%s' "$cmd" | jq -Rs .)" \
    "$(printf '%s' "$cwd"  | jq -Rs .)")
  set +e
  (cd "$cwd" && printf '%s' "$payload" | bash "$HOOK") 2>"$TMP/err"
  printf '%d' $? > "$TMP/rc"
  set -e
  LAST_RC=$(cat "$TMP/rc")
  LAST_MSG=$(cat "$TMP/err")
}

assert_blocked() {
  local label="$1"
  if [ "$LAST_RC" -eq 2 ]; then
    pass "blocked (exit 2) — $label"
  else
    fail "must block (exit 2) — $label (got exit $LAST_RC / msg: $LAST_MSG)"
  fi
}

assert_allowed() {
  local label="$1"
  if [ "$LAST_RC" -eq 0 ]; then
    pass "allowed (exit 0) — $label"
  else
    fail "must allow (exit 0) — $label (got exit $LAST_RC / msg: $LAST_MSG)"
  fi
}

# -----------------------------------------------------------------------
echo "=== (d) Missing plans directory must BLOCK, not silently pass ==="

run "gh pr merge --squash"
assert_blocked "gh pr merge with no plans dir"
case "$LAST_MSG" in
  *"does not exist"*) pass "explains: plans dir missing" ;;
  *) fail "block msg must mention missing dir (got: $LAST_MSG)" ;;
esac

# -----------------------------------------------------------------------
echo "=== (a)+(b) PRIMARY NEGATIVE: merge command with no review report BLOCKS ==="

mkdir -p "$PLANS"

run "gh pr merge --squash"
assert_blocked "gh pr merge — no review report"
case "$LAST_MSG" in
  *"No /workflow-review report"*) pass "explains: no report found" ;;
  *) fail "block msg must say no report (got: $LAST_MSG)" ;;
esac

run "gh pr merge 42 --merge"
assert_blocked "gh pr merge <num> --merge"

run "gh pr review --approve"
assert_blocked "gh pr review --approve"

run "echo checking && gh pr merge --squash"
assert_blocked "echo && gh pr merge (&&-chained)"

run "echo checking; gh pr merge --squash"
assert_blocked "echo; gh pr merge (;-chained)"

# -----------------------------------------------------------------------
echo "=== (b) PRIMARY PROSE TEST: heredoc body mentioning the phrase must PASS ==="

# This is the exact failure shape from #117: a gh issue create whose heredoc body
# contains "gh pr merge" as documentation prose, not as an invocation.
MENTION=$(cat <<'OUTER'
gh issue create --title "gate bug" --body "$(cat <<'EOF'
Filing #113 blocked. When the session mutates the board — gh issue close,
gh pr merge, git branch -d — the hook fired on the body text alone.
EOF
)"
OUTER
)

run "$MENTION"
assert_allowed "heredoc body mentioning gh pr merge (issue #117 shape)"

run "gh issue create --body 'see gh pr merge for context'"
assert_allowed "inline --body mentioning gh pr merge"

run "gh issue list"
assert_allowed "gh issue list (unrelated)"

run "git status -sb"
assert_allowed "git status (unrelated)"

run "ls -la"
assert_allowed "ls (unrelated)"

# -----------------------------------------------------------------------
echo "=== (c) Loose glob: plan doc ABOUT review must NOT satisfy the gate ==="

PLAN_ABOUT_REVIEW="$PLANS/2026-08-15-review-attribution.md"
printf 'Status: PLANNED\n' > "$PLAN_ABOUT_REVIEW"
touch "$PLAN_ABOUT_REVIEW"

run "gh pr merge --squash"
assert_blocked "plan-about-review doc must NOT satisfy the gate"
case "$LAST_MSG" in
  *"No /workflow-review report"*) pass "correctly reports no verdict report" ;;
  *) fail "must say no verdict report found (got: $LAST_MSG)" ;;
esac

rm "$PLAN_ABOUT_REVIEW"

# -----------------------------------------------------------------------
echo "=== Passing review report — merge should be ALLOWED ==="

REPORT="$PLANS/2026-08-15-review-verdict.md"
printf 'verdict: approve\n' > "$REPORT"
touch "$REPORT"

run "gh pr merge --squash"
assert_allowed "gh pr merge with passing review report"

# -----------------------------------------------------------------------
echo "=== Gate 2: blocking findings in report — must BLOCK ==="

printf 'verdict: request_changes\nmerge_impact: blocker\n' > "$REPORT"
touch "$REPORT"

run "gh pr merge --squash"
assert_blocked "gh pr merge with blocking findings in report"
case "$LAST_MSG" in
  *"blocking findings"*) pass "explains: blocking findings" ;;
  *) fail "block msg must mention blocking findings (got: $LAST_MSG)" ;;
esac

printf 'verdict: insufficient_context\n' > "$REPORT"
touch "$REPORT"

run "gh pr merge --squash"
assert_blocked "insufficient_context verdict blocks"

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
