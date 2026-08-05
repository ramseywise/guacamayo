#!/usr/bin/env bash
# Telemetry scheduled run.
#
# Mirrors librarian tools/cartographer/cartographer-cron.sh @ aa3166e (GUA-93),
# facts mode only — guacamayo's telemetry has no corpus sweep.
#
#   facts  daily — capture session JSONL into the fact table. No API key, cheap.
#                  This is the one that matters: local JSONL rotates out in ~5
#                  days, so a missed window is history lost for good.
#
# Scheduling is launchd, not crontab — cron does not fire while the Mac is asleep
# and silently skips the window; launchd re-fires on wake. See
# scripts/com.wiseer.guacamayo.telemetry.plist (Ramsey loads it manually).
#
# Usage: telemetry-cron.sh [facts]   (default: facts)

set -euo pipefail

MODE="${1:-facts}"

# Repo root is one level up from scripts/.
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# One log per mode, same convention as librarian even with a single mode today —
# a shared log file is how a daily failure gets buried (librarian #60).
case "${MODE}" in
    facts) LOG_NAME="telemetry-facts.log" ;;
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
    *)
        log "unknown mode: ${MODE} (expected facts)"
        exit 64
        ;;
esac

log "--- run finished (exit ${EXIT_CODE})"
exit "${EXIT_CODE}"
