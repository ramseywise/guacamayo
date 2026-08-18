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
