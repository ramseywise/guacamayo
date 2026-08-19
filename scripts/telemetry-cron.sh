#!/usr/bin/env bash
# Telemetry scheduled run.
#
# Mirrors librarian tools/cartographer/cartographer-cron.sh @ aa3166e (GUA-93),
# facts mode only — guacamayo's telemetry has no corpus sweep.
#
#   facts  daily — capture session JSONL into the fact table. No API key, cheap.
#                  This is the one that matters: local JSONL rotates out in ~5
#                  days, so a missed window is history lost for good.
#   board  every 600s — snapshot open issues, PRs, and branch facts into
#                  .sounding/telemetry/board.json so /wake reads state instead
#                  of re-running gh sweeps. RunAtLoad so a reboot populates it
#                  immediately rather than leaving a 10-minute hole.
#
# Scheduling is launchd, not crontab — cron does not fire while the Mac is asleep
# and silently skips the window; launchd re-fires on wake. See
# scripts/com.wiseer.guacamayo.telemetry.plist and
# scripts/com.wiseer.guacamayo.board.plist (Ramsey loads them manually).
#
# Usage: telemetry-cron.sh [facts|board]   (default: facts)

set -euo pipefail

MODE="${1:-facts}"

# Repo root is one level up from scripts/.
# TELEMETRY_CRON_REPO_DIR may override for testing (normally absent).
REPO_DIR="${TELEMETRY_CRON_REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

# One log per mode, same convention as librarian even with a single mode today —
# a shared log file is how a daily failure gets buried (librarian #60).
case "${MODE}" in
    facts) LOG_NAME="telemetry-facts.log" ;;
    board) LOG_NAME="telemetry-board.log" ;;
    *)     LOG_NAME="telemetry-unknown.log" ;;
esac
LOG_FILE="${REPO_DIR}/logs/${LOG_NAME}"

mkdir -p "$(dirname "${LOG_FILE}")"
cd "${REPO_DIR}"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "${LOG_FILE}"; }

log "--- run started (mode=${MODE}, repo=${REPO_DIR})"

# Source env vars — facts needs none today, but harmless and keeps the shape
# identical to the librarian script it mirrors.
if [ -f "${REPO_DIR}/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "${REPO_DIR}/.env"
    set +a
fi

# Fail loudly to the log rather than dying silently: `set -e` would abort before
# the failure was ever recorded, which is how a broken cron job stays invisible.
run_step() {
    local label="$1"
    shift
    log "running: $*"
    if "$@" >> "${LOG_FILE}" 2>&1; then
        log "${label}: ok"
    else
        local code=$?
        log "${label}: FAILED (exit ${code})"
        return "${code}"
    fi
}

EXIT_CODE=0

case "${MODE}" in
    facts) run_step facts uv run telemetry --facts || EXIT_CODE=$? ;;
    board)
        # --act enables the two idempotent auto-mutations (auto_close_merged,
        # auto_fix_label). DEFAULT OFF — proposals only until the actions log
        # shows proposal accuracy. To enable: uncomment the --act flag below
        # and reload the launchd plist. See GUA-119 step 6 and actions.jsonl.
        #
        # run_step board uv run telemetry --board --act || EXIT_CODE=$?
        run_step board uv run telemetry --board || EXIT_CODE=$?
        ;;
    *)
        log "unknown mode: ${MODE} (expected facts or board)"
        exit 64
        ;;
esac

log "--- run finished (exit ${EXIT_CODE})"

# ---------------------------------------------------------------------------
# Insights auto-trigger (GUA-138 Session B; headless spawn added GUA-150 step 1)
#
# After each facts run: check two conditions against the live workspace. When
# either is true, write the marker (still consumed by the next manual
# /meta-grow or /meta-wake) AND spawn `claude -p "/meta-insights"` headlessly,
# mirroring the retro spawn pattern below: lockfile + once-per-day stamp +
# spawn_insights row in actions.jsonl. The stamp bounds token cost to at most
# one spawn per day.
#
# Conditions (either → trigger):
#   1. growth.md has ≥ 3 entries (accumulation signal)
#   2. insights-log.md last run date is > 3 days ago (staleness signal)
#
# To disable: set INSIGHTS_TRIGGER_ENABLED= (empty string) below.
INSIGHTS_TRIGGER_ENABLED=1
TELEMETRY_DIR="${REPO_DIR}/.sounding/telemetry"
INSIGHTS_MARKER="${TELEMETRY_DIR}/insights-due.marker"
INSIGHTS_LOCK="${TELEMETRY_DIR}/insights-spawn.lock"
INSIGHTS_LOG="${REPO_DIR}/logs/insights-auto.log"
GROWTH_FILE="${REPO_DIR}/.sounding/growth/growth.md"
INSIGHTS_LOG_FILE="${REPO_DIR}/.sounding/insights/insights-log.md"
INSIGHTS_ACTIONS_LOG="${TELEMETRY_DIR}/actions.jsonl"
INSIGHTS_STAMP_DIR="${TELEMETRY_DIR}/stamps"
INSIGHTS_STAMP="${INSIGHTS_STAMP_DIR}/insights-spawn-$(date '+%Y-%m-%d')"

if [ "${INSIGHTS_TRIGGER_ENABLED:-}" = "1" ] && [ "${MODE}" = "facts" ]; then
    mkdir -p "$(dirname "${INSIGHTS_LOG}")"

    # --- Condition 1: growth count ---
    growth_count=0
    if [ -f "${GROWTH_FILE}" ]; then
        # `|| true`, not `|| echo 0`: grep -c already prints 0 on no match while
        # exiting 1, so `|| echo 0` would yield the two-line value "0\n0" and
        # corrupt the JSON evidence below.
        growth_count="$(grep -cE '^[0-9]{4}-[0-9]{2}-[0-9]{2}' "${GROWTH_FILE}" 2>/dev/null || true)"
        growth_count="${growth_count:-0}"
    fi

    # --- Condition 2: insights staleness ---
    insights_stale=0
    insights_last_date=""
    if [ -f "${INSIGHTS_LOG_FILE}" ]; then
        insights_last_date="$(grep -oE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}' "${INSIGHTS_LOG_FILE}" \
            | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort -r | head -1)"
        if [ -n "${insights_last_date}" ]; then
            # Days since last insights run (macOS date: -j -f parses, no -d)
            last_ts="$(date -j -f '%Y-%m-%d' "${insights_last_date}" '+%s' 2>/dev/null || echo 0)"
            now_ts="$(date '+%s')"
            days_stale=$(( (now_ts - last_ts) / 86400 ))
            if [ "${days_stale}" -gt 3 ] 2>/dev/null; then
                insights_stale=1
            fi
        else
            # No parseable date — treat as stale
            insights_stale=1
            days_stale="unknown"
        fi
    else
        insights_stale=1
        days_stale="no file"
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') insights-trigger: growth_count=${growth_count} insights_last=${insights_last_date:-none} insights_stale=${insights_stale}" >> "${INSIGHTS_LOG}"

    # Determine trigger reason
    trigger_reason=""
    if [ "${growth_count}" -ge 3 ] 2>/dev/null; then
        trigger_reason="growth_count=${growth_count} (>=3)"
    fi
    if [ "${insights_stale}" = "1" ]; then
        stale_suffix=" days_stale=${days_stale:-unknown}"
        if [ -n "${trigger_reason}" ]; then
            trigger_reason="${trigger_reason}; stale${stale_suffix}"
        else
            trigger_reason="staleness${stale_suffix}"
        fi
    fi

    if [ -n "${trigger_reason}" ]; then
        # Acquire lockfile (non-blocking mkdir) — guards both the marker write
        # and the headless spawn against a concurrent facts run.
        if ! mkdir "${INSIGHTS_LOCK}" 2>/dev/null; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') insights-trigger: lockfile held, skipping" >> "${INSIGHTS_LOG}"
            _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
            printf '%s\n' "{\"ts\":\"${_ts}\",\"action\":\"spawn_insights\",\"outcome\":\"declined\",\"reason\":\"lockfile_held\",\"evidence\":{\"growth_count\":${growth_count},\"insights_stale\":${insights_stale}}}" >> "${INSIGHTS_ACTIONS_LOG}"
        else
            ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
            # Write marker for /meta-grow or /meta-wake to consume (manual path
            # stays intact — the spawn below is the automated path)
            printf 'reason: %s\ntimestamp: %s\ngrowth_count: %s\ninsights_last: %s\n' \
                "${trigger_reason}" "${ts}" "${growth_count}" "${insights_last_date:-none}" \
                > "${INSIGHTS_MARKER}"
            echo "$(date '+%Y-%m-%d %H:%M:%S') insights-trigger: marker written (${trigger_reason})" >> "${INSIGHTS_LOG}"

            # Headless spawn (GUA-150 step 1) — once-per-day stamp bounds cost
            mkdir -p "${INSIGHTS_STAMP_DIR}"
            if [ -f "${INSIGHTS_STAMP}" ]; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') insights-spawn: already ran today (stamp exists), skipping" >> "${INSIGHTS_LOG}"
                _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
                printf '%s\n' "{\"ts\":\"${_ts}\",\"action\":\"spawn_insights\",\"outcome\":\"declined\",\"reason\":\"already_ran_today\",\"evidence\":{\"growth_count\":${growth_count},\"insights_stale\":${insights_stale}}}" >> "${INSIGHTS_ACTIONS_LOG}"
            else
                echo "$(date '+%Y-%m-%d %H:%M:%S') insights-spawn: spawning /meta-insights (sonnet) — ${trigger_reason}" >> "${INSIGHTS_LOG}"
                touch "${INSIGHTS_STAMP}"
                spawn_outcome="acted"
                spawn_error=""
                if claude -p "/meta-insights" --model sonnet >> "${LOG_FILE}" 2>&1; then
                    echo "$(date '+%Y-%m-%d %H:%M:%S') insights-spawn: claude exited 0" >> "${INSIGHTS_LOG}"
                else
                    spawn_outcome="declined"
                    spawn_error="claude exited non-zero"
                    echo "$(date '+%Y-%m-%d %H:%M:%S') insights-spawn: FAILED — ${spawn_error}" >> "${INSIGHTS_LOG}"
                fi
                _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
                if [ "${spawn_outcome}" = "acted" ]; then
                    printf '%s\n' "{\"ts\":\"${_ts}\",\"action\":\"spawn_insights\",\"outcome\":\"acted\",\"reason\":\"${trigger_reason}\",\"evidence\":{\"growth_count\":${growth_count},\"insights_stale\":${insights_stale}}}" >> "${INSIGHTS_ACTIONS_LOG}"
                else
                    printf '%s\n' "{\"ts\":\"${_ts}\",\"action\":\"spawn_insights\",\"outcome\":\"declined\",\"reason\":\"${spawn_error}\",\"evidence\":{\"growth_count\":${growth_count},\"insights_stale\":${insights_stale}}}" >> "${INSIGHTS_ACTIONS_LOG}"
                fi
            fi
            rmdir "${INSIGHTS_LOCK}"
        fi
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') insights-trigger: no trigger (growth=${growth_count}, stale=${insights_stale})" >> "${INSIGHTS_LOG}"
    fi
fi

# ---------------------------------------------------------------------------
# Step 7 — Unattended retro spawn (GUA-119 sub-issue C)
#
# After every board tick: compare retro_due vs retro_acked in cascade-state.json.
# Absent key counts as 0 (the #116 comparison — meta-grow/SKILL.md:154-156).
# When due: acquire a lockfile and a once-per-day stamp, then spawn /meta-retro
# via `claude -p`. The spawn does NOT self-ack — ack stays on the verify-then-ack
# path in meta-grow/meta-dream (#116 convention).
#
# To disable: comment out the RETRO_SPAWN_ENABLED line below.
RETRO_SPAWN_ENABLED=1
TELEMETRY_DIR="${REPO_DIR}/.sounding/telemetry"
CASCADE_STATE="${TELEMETRY_DIR}/cascade-state.json"
ACTIONS_LOG="${TELEMETRY_DIR}/actions.jsonl"
RETRO_LOCK="${TELEMETRY_DIR}/retro-spawn.lock"
RETRO_STAMP_DIR="${TELEMETRY_DIR}/stamps"
RETRO_STAMP="${RETRO_STAMP_DIR}/retro-spawn-$(date '+%Y-%m-%d')"

if [ "${RETRO_SPAWN_ENABLED:-}" = "1" ] && [ "${MODE}" = "board" ]; then
    if [ ! -f "${CASCADE_STATE}" ]; then
        log "retro-spawn: cascade-state.json missing, skipping"
    else
        retro_due="$(jq -r '(.retro_due // 0)' "${CASCADE_STATE}" 2>/dev/null || echo 0)"
        retro_acked="$(jq -r '(.retro_acked // 0)' "${CASCADE_STATE}" 2>/dev/null || echo 0)"
        log "retro-spawn: retro_due=${retro_due} retro_acked=${retro_acked}"

        if [ "${retro_due}" -gt "${retro_acked}" ] 2>/dev/null; then
            # Acquire lockfile (exclusive, non-blocking)
            if ! mkdir "${RETRO_LOCK}" 2>/dev/null; then
                log "retro-spawn: lockfile held, skipping"
                _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
                printf '%s\n' "{\"ts\":\"${_ts}\",\"action\":\"spawn_retro\",\"outcome\":\"declined\",\"reason\":\"lockfile_held\",\"evidence\":{\"retro_due\":${retro_due},\"retro_acked\":${retro_acked}}}" >> "${ACTIONS_LOG}"
            else
                # Check once-per-day stamp
                mkdir -p "${RETRO_STAMP_DIR}"
                if [ -f "${RETRO_STAMP}" ]; then
                    log "retro-spawn: already ran today (stamp exists), skipping"
                    rmdir "${RETRO_LOCK}"
                    _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
                    printf '%s\n' "{\"ts\":\"${_ts}\",\"action\":\"spawn_retro\",\"outcome\":\"declined\",\"reason\":\"already_ran_today\",\"evidence\":{\"retro_due\":${retro_due},\"retro_acked\":${retro_acked}}}" >> "${ACTIONS_LOG}"
                else
                    log "retro-spawn: spawning /meta-retro (sonnet)"
                    touch "${RETRO_STAMP}"
                    spawn_outcome="acted"
                    spawn_error=""
                    if claude -p "/meta-retro" --model sonnet >> "${LOG_FILE}" 2>&1; then
                        log "retro-spawn: claude exited 0"
                    else
                        spawn_outcome="declined"
                        spawn_error="claude exited non-zero"
                        log "retro-spawn: FAILED — ${spawn_error}"
                    fi
                    rmdir "${RETRO_LOCK}"
                    _ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
                    if [ "${spawn_outcome}" = "acted" ]; then
                        printf '%s\n' "{\"ts\":\"${_ts}\",\"action\":\"spawn_retro\",\"outcome\":\"acted\",\"reason\":\"retro_due_gt_acked\",\"evidence\":{\"retro_due\":${retro_due},\"retro_acked\":${retro_acked}}}" >> "${ACTIONS_LOG}"
                    else
                        printf '%s\n' "{\"ts\":\"${_ts}\",\"action\":\"spawn_retro\",\"outcome\":\"declined\",\"reason\":\"${spawn_error}\",\"evidence\":{\"retro_due\":${retro_due},\"retro_acked\":${retro_acked}}}" >> "${ACTIONS_LOG}"
                    fi
                fi
            fi
        else
            log "retro-spawn: retro_due (${retro_due}) <= retro_acked (${retro_acked}), no spawn needed"
        fi
    fi
fi

exit "${EXIT_CODE}"
