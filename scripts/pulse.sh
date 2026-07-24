#!/bin/bash
# pulse.sh — Generate live cross-repo status for the dashboard pulse section.
# Called by: make pulse, /grow skill
# Writes: replaces the <section id="pulse"> block in .sounding/context-dashboard.html
set -euo pipefail

DASHBOARD=".sounding/context-dashboard.html"
REPOS="guacamayo listen-wiseer learn-ai-engineering atlas ai-project-template librarian job-system playground lebanese-blonde"
OWNER="ramseywise"
NOW=$(date '+%Y-%m-%d %H:%M')

# ── Collect data ──────────────────────────────────────────────────────────────

# Growth entries
GROWTH_COUNT=$(grep -cE '^[0-9]{4}-' .sounding/growth.md 2>/dev/null || true)
GROWTH_COUNT=${GROWTH_COUNT:-0}
if [ "$GROWTH_COUNT" -ge 5 ]; then
  GROWTH_NOTE='<div class="tile-note" style="color:var(--warn)">synthesis due at /dream</div>'
elif [ "$GROWTH_COUNT" -eq 0 ]; then
  GROWTH_NOTE='<div class="tile-note" style="color:var(--good)">clear</div>'
else
  GROWTH_NOTE=""
fi

# Retro status
INSIGHTS_DATE=$(head -5 .sounding/insights-log.md 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 || echo "unknown")
if [ "$INSIGHTS_DATE" != "unknown" ]; then
  INSIGHTS_EPOCH=$(date -j -f '%Y-%m-%d' "$INSIGHTS_DATE" '+%s' 2>/dev/null || echo "0")
  NOW_EPOCH=$(date '+%s')
  DAYS_AGO=$(( (NOW_EPOCH - INSIGHTS_EPOCH) / 86400 ))
  if [ "$DAYS_AGO" -ge 7 ]; then
    RETRO_VALUE="${DAYS_AGO}d ago"
    RETRO_NOTE='<div class="tile-note" style="color:var(--bad)">overdue (&ge;7d)</div>'
  else
    RETRO_VALUE="${DAYS_AGO}d ago"
    RETRO_NOTE='<div class="tile-note" style="color:var(--good)">current</div>'
  fi
else
  RETRO_VALUE="unknown"
  RETRO_NOTE=""
fi

# Hypotheses
HYPO_COUNT=$(grep -c '| hypothesis' .sounding/tooling-ledger.md 2>/dev/null || echo "0")

# ── PRs across repos ─────────────────────────────────────────────────────────

PR_ROWS=""
PR_TOTAL=0
for repo in $REPOS; do
  prs=$(gh pr list --repo "$OWNER/$repo" --state open --json number,title,headBranch,updatedAt \
    --jq '.[] | "\(.number)\t\(.title)\t\(.headBranch)\t\(.updatedAt[:10])"' 2>/dev/null || true)
  if [ -n "$prs" ]; then
    while IFS=$'\t' read -r num title branch updated; do
      PR_ROWS="${PR_ROWS}          <tr><td>${repo}</td><td>#${num}</td><td>${title}</td><td>${branch}</td><td>${updated}</td></tr>\n"
      PR_TOTAL=$((PR_TOTAL + 1))
    done <<< "$prs"
  fi
done

if [ "$PR_TOTAL" -eq 0 ]; then
  PR_SECTION='<p class="card-note" style="color:var(--good)">No open PRs across repos.</p>'
else
  PR_SECTION=$(printf '<div class="overflow-x">\n      <table class="issue-table">\n        <thead><tr><th>Repo</th><th>#</th><th>Title</th><th>Branch</th><th>Updated</th></tr></thead>\n        <tbody>\n%b        </tbody>\n      </table>\n      </div>' "$PR_ROWS")
fi

# ── Issues across repos ──────────────────────────────────────────────────────

ISSUE_ROWS=""
ISSUE_SUMMARY=""
TOTAL_ISSUES=0
for repo in $REPOS; do
  issues=$(gh issue list --repo "$OWNER/$repo" --state open --json number,title,labels \
    --jq '.[] | "\(.number)\t\(.title)\t\(.labels | map(.name) | join(","))"' --limit 100 2>/dev/null || true)
  if [ -n "$issues" ]; then
    repo_count=0
    ready_count=0
    progress_count=0
    backlog_count=0
    while IFS=$'\t' read -r num title labels; do
      repo_count=$((repo_count + 1))
      # Determine state chip
      if echo "$labels" | grep -q "in-progress"; then
        chip='<span class="status-chip executing">in-progress</span>'
        progress_count=$((progress_count + 1))
      elif echo "$labels" | grep -q "ready"; then
        chip='<span class="status-chip ready">ready</span>'
        ready_count=$((ready_count + 1))
      elif echo "$labels" | grep -q "refinement"; then
        chip='<span class="status-chip planned">refinement</span>'
      elif echo "$labels" | grep -q "blocked"; then
        chip='<span class="status-chip" style="background:var(--bad-bg);color:var(--bad)">blocked</span>'
      else
        chip='<span class="status-chip backlog">backlog</span>'
        backlog_count=$((backlog_count + 1))
      fi
      ISSUE_ROWS="${ISSUE_ROWS}          <tr><td>${repo}</td><td>#${num}</td><td>${title}</td><td>${chip}</td></tr>\n"
    done <<< "$issues"
    TOTAL_ISSUES=$((TOTAL_ISSUES + repo_count))
    ISSUE_SUMMARY="${ISSUE_SUMMARY}${repo}:${repo_count} "
  fi
done

# ── Plan docs (recently modified, non-EXECUTED) ──────────────────────────────

PLAN_ROWS=""
while IFS= read -r planfile; do
  [ -z "$planfile" ] && continue
  status_line=$(head -5 "$planfile" | grep -i '^Status:' || true)
  [ -z "$status_line" ] && continue
  # Skip finished plans
  echo "$status_line" | grep -qiE 'EXECUTED|COMPLETE|DONE|SUPERSEDED|ABANDONED' && continue

  plan_name=$(basename "$planfile" .md)
  repo_name=$(echo "$planfile" | sed 's|.*/workspace/||;s|/\.claude/.*||')

  if echo "$status_line" | grep -qi 'IN.PROGRESS'; then
    chip='<span class="status-chip executing">in-progress</span>'
  elif echo "$status_line" | grep -qi 'PLANNED'; then
    chip='<span class="status-chip planned">planned</span>'
  elif echo "$status_line" | grep -qiE 'BLOCKED|GATED'; then
    chip='<span class="status-chip" style="background:var(--bad-bg);color:var(--bad)">blocked</span>'
  elif echo "$status_line" | grep -qi 'RESEARCH'; then
    chip='<span class="status-chip ready">research</span>'
  else
    chip='<span class="status-chip backlog">other</span>'
  fi

  PLAN_ROWS="${PLAN_ROWS}          <tr><td>${repo_name}</td><td>${plan_name}</td><td>${chip}</td></tr>\n"
done < <(find "$HOME/workspace" -path '*/.claude/docs/plans/*.md' -mtime -7 2>/dev/null | sort -r)

# ── Assemble HTML ─────────────────────────────────────────────────────────────

PULSE_HTML=$(cat <<HEREDOC
  <section class="tab-content active" id="pulse">
    <div class="section-header">
      <h2>Session Pulse</h2>
      <p class="section-question">What's in flight? What needs attention?</p>
    </div>

    <div class="explainer">
      <strong>Live signal from /grow</strong> — last refreshed ${NOW}. Cross-repo status from GitHub + plan docs.
    </div>

    <!-- Status tiles -->
    <div class="pulse-grid">
      <div class="pulse-tile">
        <div class="tile-label">Last pulse</div>
        <div class="tile-value">${NOW}</div>
      </div>
      <div class="pulse-tile">
        <div class="tile-label">Growth entries</div>
        <div class="tile-value">${GROWTH_COUNT} pending</div>
        ${GROWTH_NOTE}
      </div>
      <div class="pulse-tile">
        <div class="tile-label">Retro status</div>
        <div class="tile-value">${RETRO_VALUE}</div>
        ${RETRO_NOTE}
      </div>
      <div class="pulse-tile">
        <div class="tile-label">Hypotheses</div>
        <div class="tile-value">${HYPO_COUNT} pending</div>
      </div>
    </div>

    <!-- Open PRs -->
    <div class="card">
      <div class="card-title">Open PRs (${PR_TOTAL})</div>
      <p class="card-note">Merge queue across repos.</p>
      ${PR_SECTION}
    </div>

    <!-- Active plans -->
    <div class="card">
      <div class="card-title">Active plans</div>
      <p class="card-note">Plan docs modified in last 7 days that aren't finished.</p>
      <div class="overflow-x">
      <table class="issue-table">
        <thead><tr><th>Repo</th><th>Plan</th><th>Status</th></tr></thead>
        <tbody>
$(printf '%b' "$PLAN_ROWS")        </tbody>
      </table>
      </div>
    </div>

    <!-- Issues board -->
    <div class="card">
      <div class="card-title">Issues board (${TOTAL_ISSUES} open)</div>
      <p class="card-note">All open GitHub issues across repos. ${ISSUE_SUMMARY}</p>
      <div class="overflow-x">
      <table class="issue-table">
        <thead><tr><th>Repo</th><th>#</th><th>Title</th><th>State</th></tr></thead>
        <tbody>
$(printf '%b' "$ISSUE_ROWS")        </tbody>
      </table>
      </div>
    </div>
  </section>
HEREDOC
)

# ── Write to dashboard ────────────────────────────────────────────────────────

if [ ! -f "$DASHBOARD" ]; then
  echo "ERROR: $DASHBOARD not found" >&2
  exit 1
fi

# Replace the pulse section (between <section...id="pulse"> and the next </section>)
# Use python for reliable multi-line replacement
python3 -c "
import re, sys
with open('$DASHBOARD', 'r') as f:
    content = f.read()
# Match the pulse section
pattern = r'  <section class=\"tab-content[^\"]*\" id=\"pulse\">.*?</section>'
replacement = sys.stdin.read()
new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
if new_content == content:
    print('WARNING: pulse section not found in dashboard', file=sys.stderr)
    sys.exit(1)
with open('$DASHBOARD', 'w') as f:
    f.write(new_content)
print(f'Pulse updated: {len(replacement)} chars written')
" <<< "$PULSE_HTML"
