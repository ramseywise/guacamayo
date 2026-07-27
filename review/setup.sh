#!/usr/bin/env bash
# review/setup.sh — idempotent symlink setup for the review package.
#
# Creates ~/.claude/refs/ symlinks pointing at guacamayo/review/refs/ canonical copies.
# Safe to re-run: existing symlinks are overwritten, real files are left untouched.
#
# Usage:
#   cd ~/workspace/guacamayo
#   bash review/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REVIEW_REFS="$SCRIPT_DIR/refs"
CLAUDE_REFS="$HOME/.claude/refs"

if [[ ! -d "$CLAUDE_REFS" ]]; then
  echo "ERROR: $CLAUDE_REFS does not exist. Is ~/.claude set up?" >&2
  exit 1
fi

REFS=(
  finding-schema.md
  evidence-model.md
  review-dimensions.md
  review-dod.md
  models.md
)

echo "Linking review refs: $REVIEW_REFS -> $CLAUDE_REFS"
for ref in "${REFS[@]}"; do
  src="$REVIEW_REFS/$ref"
  dst="$CLAUDE_REFS/$ref"
  if [[ ! -f "$src" ]]; then
    echo "  SKIP (source missing): $ref"
    continue
  fi
  if [[ -L "$dst" ]]; then
    current="$(readlink "$dst")"
    if [[ "$current" == "$src" ]]; then
      echo "  OK (already linked): $ref"
      continue
    fi
    echo "  UPDATE: $ref ($current -> $src)"
    ln -sf "$src" "$dst"
  elif [[ -f "$dst" ]]; then
    echo "  SKIP (real file exists, not overwriting): $dst" >&2
    echo "    To update: rm $dst && ln -sf $src $dst"
  else
    echo "  CREATE: $ref"
    ln -sf "$src" "$dst"
  fi
done

echo "Done."
