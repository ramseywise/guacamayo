#!/usr/bin/env bash
# Initialize the orphan `telemetry-state` branch with an empty signals.jsonl.
#
# Run ONCE, from the main guacamayo checkout (not a worktree), after the
# GUA-118 PR has merged. The branch must not exist yet — the script will
# error if it does.
#
# Usage:
#   cd ~/workspace/guacamayo
#   bash scripts/init-telemetry-state-branch.sh
#
# After this script exits, push the branch:
#   git push origin telemetry-state
#
# The board-signal GitHub Actions workflow then appends JSON lines to
# signals.jsonl on every PR / issue event and pushes the commit. The local
# board tick shallow-fetches this branch and folds signals.jsonl into the
# `signals` array in board.json.
#
# IMPORTANT: run from a CLEAN working tree with nothing staged. This script
# uses `git checkout --orphan` which stages all tracked files; it immediately
# removes them so only signals.jsonl is staged for the init commit.

set -euo pipefail

BRANCH="telemetry-state"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_DIR}"

if git rev-parse --verify --quiet "${BRANCH}" > /dev/null 2>&1; then
    echo "ERROR: branch '${BRANCH}' already exists. Delete it first if you want to reinitialize."
    exit 1
fi

# Local-only rev-parse says nothing about the remote: a branch that exists on
# origin but not here would pass the check above and then collide on push.
if [ -n "$(git ls-remote --heads origin "${BRANCH}" 2> /dev/null)" ]; then
    echo "ERROR: branch '${BRANCH}' already exists on origin. Fetch it instead of reinitializing."
    exit 1
fi

# `git checkout --orphan` does NOT refuse a dirty tree — it carries uncommitted
# changes onto the new branch, and the `git rm -rf .` below then deletes them
# from the working tree with no commit to recover from. Refuse to run dirty.
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: working tree is not clean. Commit or stash first —"
    echo "       this script runs 'git rm -rf .' and uncommitted work would be destroyed."
    git status --short
    exit 1
fi

echo "Creating orphan branch: ${BRANCH}"
git checkout --orphan "${BRANCH}"
git rm -rf . --quiet

# Empty JSONL file — the workflow appends one JSON object per event.
echo '# signals.jsonl — appended by board-signal.yml on PR/issue events' > signals.jsonl
git add signals.jsonl

# Commit. Note: this must be run by Ramsey (not the agent) because the
# branch-guard hook rejects non-convention branch names in agent sessions.
git commit -m "chore(telemetry): initialize telemetry-state signal branch (GUA-118)"

echo ""
echo "Branch '${BRANCH}' initialized. Now push it:"
echo "  git push origin ${BRANCH}"
echo ""
echo "Then return to main:"
echo "  git checkout main"
