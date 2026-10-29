#!/bin/bash
# hygiene.sh — Cross-repo branch cleanup + staging verification.
# Called by: make hygiene
# Prunes stale remote refs, deletes merged/empty branches, reports staged changes.
set -euo pipefail

OWNER="ramseywise"
DRY_RUN="${1:-}"
GUACAMAYO="$(cd "$(dirname "$0")/.." && pwd)"

# The repo list is repos.toml, read through the telemetry CLI so bash never parses TOML.
# Read it up front: a registry failure must stop the run, not yield an empty loop.
REGISTRY="$(uv run --project "$GUACAMAYO" telemetry --list-repos)"

# fd 3, not stdin: the gh/git calls in the loop body must not be able to eat the list.
while IFS=$'\t' read -r repo dir <&3; do
  if [ ! -d "$dir/.git" ]; then
    echo "=== $repo ==="
    echo "  NOT CLONED: $dir"
    echo
    continue
  fi
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
    # shellcheck disable=SC2001  # sed prepends to each line; ${var//^/prefix} can't do this
    echo "$staged" | sed 's/^/    /'
  fi

  # Report uncommitted changes
  modified=$(git status --short 2>/dev/null)
  if [ -n "$modified" ]; then
    echo "  UNCOMMITTED:"
    # shellcheck disable=SC2001  # sed prepends to each line; ${var//^/prefix} can't do this
    echo "$modified" | sed 's/^/    /'
  fi

  echo
done 3<<< "$REGISTRY"

echo "Done. Pass --dry-run to preview without deleting."
