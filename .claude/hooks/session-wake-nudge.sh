#!/usr/bin/env bash
# session-wake-nudge.sh — SessionStart hook (GUA-150 step 2).
# Emits the wake nudge as a JSON context block, extended from static text to a
# live status: cascade state (compacts, grows_due), board staleness, growth count.
#
# Must never fail the session start: every read degrades to "?" and the JSON
# always emits — a broken status line is still a nudge.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TELEMETRY_DIR="${REPO_DIR}/.sounding/telemetry"
CASCADE_STATE="${TELEMETRY_DIR}/cascade-state.json"
BOARD="${TELEMETRY_DIR}/board.json"
GROWTH_FILE="${REPO_DIR}/.sounding/growth/growth.md"

# --- cascade state ---
compacts="?"
grows_due="?"
if [ -f "${CASCADE_STATE}" ] && command -v jq >/dev/null 2>&1; then
    compacts="$(jq -r '(.compacts // 0)' "${CASCADE_STATE}" 2>/dev/null || echo '?')"
    grows_due="$(jq -r '(.grows_due // 0)' "${CASCADE_STATE}" 2>/dev/null || echo '?')"
fi

# --- board staleness ---
board_status="missing"
if [ -f "${BOARD}" ] && command -v jq >/dev/null 2>&1; then
    collected_at="$(jq -r '(.collected_at // empty)' "${BOARD}" 2>/dev/null || true)"
    if [ -n "${collected_at:-}" ]; then
        # macOS date: -j -f parses; strip fractional seconds if present
        clean_ts="$(echo "${collected_at}" | sed -E 's/\.[0-9]+//; s/Z$//; s/\+00:00$//')"
        collected_ts="$(date -ju -f '%Y-%m-%dT%H:%M:%S' "${clean_ts}" '+%s' 2>/dev/null || echo 0)"
        if [ "${collected_ts}" -gt 0 ] 2>/dev/null; then
            age_min=$(( ($(date '+%s') - collected_ts) / 60 ))
            if [ "${age_min}" -gt 30 ]; then
                board_status="STALE (${age_min}m old — board ticks every 10m)"
            else
                board_status="fresh (${age_min}m old)"
            fi
        else
            board_status="unparseable collected_at"
        fi
    fi
fi

# --- growth count ---
growth_count=0
if [ -f "${GROWTH_FILE}" ]; then
    growth_count="$(grep -cE '^[0-9]{4}-[0-9]{2}-[0-9]{2}' "${GROWTH_FILE}" 2>/dev/null || true)"
    growth_count="${growth_count:-0}"
fi

content="Identity workspace (Sounding): run /meta-wake before starting work.
cascade: compacts=${compacts}, grows_due=${grows_due}
board: ${board_status}
growth: ${growth_count} entries"

if command -v jq >/dev/null 2>&1; then
    jq -n --arg c "${content}" '{type: "context", content: $c}'
else
    # jq missing — fall back to the static nudge (no dynamic parts to escape)
    printf '{"type": "context", "content": "Identity workspace (Sounding): run /meta-wake before starting work."}'
fi
exit 0
