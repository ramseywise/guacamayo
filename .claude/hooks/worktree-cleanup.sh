#!/usr/bin/env bash
# worktree-cleanup.sh — Stop/SubagentStop hook
# Prunes stale worktree refs and removes leftover worktree directories.
# Runs after agent completion to prevent pre-commit SKIP noise from orphaned worktrees.
#
# Bypass: SKIP_WORKTREE_CLEANUP=1

set -euo pipefail

[ "${SKIP_WORKTREE_CLEANUP:-0}" = "1" ] && exit 0

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

cd "$repo_root"

git worktree prune 2>/dev/null || true

# Check for remaining non-main worktrees that look like agent leftovers
leftover=$(git worktree list --porcelain 2>/dev/null \
  | grep '^worktree ' \
  | grep -v "^worktree $repo_root$" \
  | sed 's/^worktree //' \
  || true)

[ -z "$leftover" ] && exit 0

removed=0
for wt in $leftover; do
  case "$wt" in
    */.worktrees/*|*/agent-*)
      if git worktree remove --force "$wt" 2>/dev/null; then
        removed=$((removed + 1))
      fi
      ;;
  esac
done

if [ "$removed" -gt 0 ]; then
  echo "Cleaned up $removed leftover worktree(s)."
fi

exit 0
