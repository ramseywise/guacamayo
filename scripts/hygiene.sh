#!/bin/bash
# hygiene.sh — Cross-repo branch cleanup + staging verification.
# Called by: make hygiene
# Prunes stale remote refs, deletes merged/empty branches, reports staged changes.
set -euo pipefail

REPOS="guacamayo listen-wiseer learn-ai-engineering atlas ai-project-template librarian"
OWNER="ramseywise"
BASE="$HOME/workspace"
DRY_RUN="${1:-}"

for repo in $REPOS; do
  dir="$BASE/$repo"
  [ -d "$dir/.git" ] || continue
  cd "$dir"

  echo "=== $repo ==="

  # Prune stale remote refs
  git remote prune origin 2>/dev/null

  # Find branches that are not main/HEAD/dependabot
  stale=""
  while IFS= read -r ref; do
    branch="${ref#origin/}"
    [ -z "$branch" ] && continue

    # Check if branch's PR was merged
    merged=$(gh pr list --repo "$OWNER/$repo" --state merged --head "$branch" --json number --jq '.[0].number' 2>/dev/null || true)
    if [ -n "$merged" ]; then
      echo "  DELETE (merged PR #$merged): $branch"
      [ "$DRY_RUN" != "--dry-run" ] && git push origin --delete "$branch" 2>/dev/null || true
      continue
    fi

    # Check if branch has unique commits
    count=$(git log "origin/$branch" --not origin/main --oneline --no-merges 2>/dev/null | wc -l | tr -d ' ')
    date=$(git log "origin/$branch" -1 --format='%ci' 2>/dev/null | cut -d' ' -f1)

    if [ "$count" -eq 0 ]; then
      echo "  DELETE (empty): $branch"
      [ "$DRY_RUN" != "--dry-run" ] && git push origin --delete "$branch" 2>/dev/null || true
    else
      echo "  STALE ($count commits, last $date): $branch"
      stale="$stale $branch"
    fi
  done < <(git branch -r | grep -v 'origin/main' | grep -v 'origin/HEAD' | grep -v dependabot | sed 's|^ *||')

  # Report staged changes
  staged=$(git diff --cached --stat 2>/dev/null)
  if [ -n "$staged" ]; then
    echo "  STAGED:"
    echo "$staged" | sed 's/^/    /'
  fi

  # Report uncommitted changes
  modified=$(git status --short 2>/dev/null)
  if [ -n "$modified" ]; then
    echo "  UNCOMMITTED:"
    echo "$modified" | sed 's/^/    /'
  fi

  echo
done

echo "Done. Pass --dry-run to preview without deleting."
