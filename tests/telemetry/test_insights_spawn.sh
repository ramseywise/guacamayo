#!/usr/bin/env bash
# tests/telemetry/test_insights_spawn.sh — Shell-level tests for the GUA-150
# insights headless spawn (facts mode), mirroring test_retro_spawn.sh.
#
# Tests:
#   (a) trigger (growth >= 3) → marker written + exactly one spawn
#   (b) second run same day → marker rewritten, no spawn (stamp guard)
#   (c) no trigger (growth < 3, insights fresh) → no marker, no spawn
#   (d) lockfile held → no spawn, declined row
#
# The stub `claude` records its argv to a file; we assert on it.
# Run: bash tests/telemetry/test_insights_spawn.sh

# Note: -e is intentionally omitted — grep exits 1 on 0 matches, which would
# abort the test script before we could record the failure. We rely on
# explicit return-code checks for each assertion instead.
set -uo pipefail

REPO_SRC="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="${REPO_SRC}/scripts/telemetry-cron.sh"

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# ---------------------------------------------------------------------------
# count_in FILE PATTERN — count lines matching PATTERN in FILE.
# Returns 0 (integer) when no match or file missing; never exits non-zero.
# Uses fixed-string (-F) grep to avoid regex interpretation of special chars.
# ---------------------------------------------------------------------------
count_in() {
    local file="$1" pattern="$2"
    if [ ! -f "${file}" ]; then
        echo 0
        return
    fi
    local n
    n="$(grep -cF "${pattern}" "${file}" 2>/dev/null)" || n=0
    echo "${n}"
}

# ---------------------------------------------------------------------------
# Setup: isolated tmp environment
#
# The script derives REPO_DIR from TELEMETRY_CRON_REPO_DIR (our override).
# We create a minimal fake repo layout under TEST_TMP/repo.
# ---------------------------------------------------------------------------

TEST_TMP=""
FAKE_REPO=""
TELEMETRY_DIR=""
ACTIONS_LOG=""
INSIGHTS_MARKER=""
INSIGHTS_LOCK=""
GROWTH_FILE=""
INSIGHTS_LOG_FILE=""
CLAUDE_ARGV_LOG=""
CLAUDE_BIN=""

setup() {
    TEST_TMP="$(mktemp -d)"
    FAKE_REPO="${TEST_TMP}/repo"
    TELEMETRY_DIR="${FAKE_REPO}/.sounding/telemetry"
    ACTIONS_LOG="${TELEMETRY_DIR}/actions.jsonl"
    INSIGHTS_MARKER="${TELEMETRY_DIR}/insights-due.marker"
    INSIGHTS_LOCK="${TELEMETRY_DIR}/insights-spawn.lock"
    GROWTH_FILE="${FAKE_REPO}/.sounding/growth/growth.md"
    INSIGHTS_LOG_FILE="${FAKE_REPO}/.sounding/insights/insights-log.md"
    CLAUDE_ARGV_LOG="${TEST_TMP}/claude-argv.log"
    CLAUDE_BIN="${TEST_TMP}/bin"

    mkdir -p "${FAKE_REPO}/logs"
    mkdir -p "${TELEMETRY_DIR}"
    mkdir -p "$(dirname "${GROWTH_FILE}")"
    mkdir -p "$(dirname "${INSIGHTS_LOG_FILE}")"
    mkdir -p "${CLAUDE_BIN}"
    touch "${CLAUDE_ARGV_LOG}"

    # Stub: claude records argv, exits 0
    cat > "${CLAUDE_BIN}/claude" <<EOF
#!/usr/bin/env bash
echo "\$@" >> "${CLAUDE_ARGV_LOG}"
exit 0
EOF
    chmod +x "${CLAUDE_BIN}/claude"

    # Stub: uv exits 0 (facts run)
    cat > "${CLAUDE_BIN}/uv" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
    chmod +x "${CLAUDE_BIN}/uv"

    export CLAUDE_ARGV_LOG
}

teardown() {
    rm -rf "${TEST_TMP}"
    TEST_TMP=""
}

# write_growth N — growth.md with N dated entry lines
write_growth() {
    local n="$1" i
    : > "${GROWTH_FILE}"
    for i in $(seq 1 "${n}"); do
        echo "2026-08-1${i} [discovered] entry ${i}" >> "${GROWTH_FILE}"
    done
}

# write_insights_fresh — insights-log.md dated today (not stale)
write_insights_fresh() {
    printf '## %s — run\n\nfindings\n' "$(date '+%Y-%m-%d')" > "${INSIGHTS_LOG_FILE}"
}

run_facts() {
    # TELEMETRY_CRON_REPO_DIR overrides REPO_DIR inside the script.
    TELEMETRY_CRON_REPO_DIR="${FAKE_REPO}" \
    PATH="${CLAUDE_BIN}:${PATH}" \
        bash "${SCRIPT}" facts 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# (a) trigger (growth >= 3) → marker written + exactly one spawn
# ---------------------------------------------------------------------------

test_trigger_spawns_once() {
    setup
    write_growth 3
    write_insights_fresh   # isolate to the growth condition

    run_facts

    if [ -f "${INSIGHTS_MARKER}" ]; then
        pass "(a) marker written on trigger"
    else
        fail "(a) marker missing after trigger"
    fi

    local n
    n="$(count_in "${CLAUDE_ARGV_LOG}" "/meta-insights")"
    if [ "${n}" = "1" ]; then
        pass "(a) trigger spawns exactly once (claude calls=${n})"
    else
        fail "(a) expected 1 claude call, got: ${n}"
    fi

    local a
    a="$(count_in "${ACTIONS_LOG}" '"action":"spawn_insights","outcome":"acted"')"
    if [ "${a}" = "1" ]; then
        pass "(a) actions.jsonl has 1 acted spawn_insights"
    else
        fail "(a) expected 1 acted spawn_insights in actions.jsonl, got: ${a} (log: $(cat "${ACTIONS_LOG}" 2>/dev/null || echo '<missing>'))"
    fi

    local m
    m="$(count_in "${CLAUDE_ARGV_LOG}" "sonnet")"
    if [ "${m}" -ge "1" ] 2>/dev/null; then
        pass "(a) claude argv contains 'sonnet' (--model sonnet)"
    else
        fail "(a) claude argv missing 'sonnet' (log: $(cat "${CLAUDE_ARGV_LOG}" 2>/dev/null || echo '<missing>'))"
    fi

    teardown
}

# ---------------------------------------------------------------------------
# (b) second run same day → no second spawn (stamp guard), marker still written
# ---------------------------------------------------------------------------

test_second_run_same_day_no_spawn() {
    setup
    write_growth 3
    write_insights_fresh

    # First run — populates stamp
    run_facts

    # Reset argv log and marker; keep stamp and actions log
    printf '' > "${CLAUDE_ARGV_LOG}"
    rm -f "${INSIGHTS_MARKER}"

    # Second run same day — stamp is already present
    run_facts

    local n
    n="$(count_in "${CLAUDE_ARGV_LOG}" "/meta-insights")"
    if [ "${n}" = "0" ]; then
        pass "(b) second run same day produced no claude spawn"
    else
        fail "(b) expected 0 claude calls on second run, got: ${n}"
    fi

    if [ -f "${INSIGHTS_MARKER}" ]; then
        pass "(b) marker still written on second run (manual path intact)"
    else
        fail "(b) marker missing on second run"
    fi

    local declined
    declined="$(count_in "${ACTIONS_LOG}" '"action":"spawn_insights","outcome":"declined","reason":"already_ran_today"')"
    if [ "${declined}" -ge "1" ] 2>/dev/null; then
        pass "(b) actions.jsonl contains already_ran_today declined record"
    else
        fail "(b) missing already_ran_today declined record in actions.jsonl (log: $(cat "${ACTIONS_LOG}" 2>/dev/null || echo '<missing>'))"
    fi

    teardown
}

# ---------------------------------------------------------------------------
# (c) no trigger (growth < 3, insights fresh) → no marker, no spawn
# ---------------------------------------------------------------------------

test_no_trigger_no_spawn() {
    setup
    write_growth 2
    write_insights_fresh

    run_facts

    if [ ! -f "${INSIGHTS_MARKER}" ]; then
        pass "(c) no marker when below thresholds"
    else
        fail "(c) unexpected marker written: $(cat "${INSIGHTS_MARKER}")"
    fi

    local n
    n="$(count_in "${CLAUDE_ARGV_LOG}" "/meta-insights")"
    if [ "${n}" = "0" ]; then
        pass "(c) no trigger → no spawn"
    else
        fail "(c) expected no spawn without trigger, got claude calls: ${n}"
    fi

    local s
    s="$(count_in "${ACTIONS_LOG}" '"action":"spawn_insights"')"
    if [ "${s}" = "0" ]; then
        pass "(c) no spawn_insights line in actions.jsonl without trigger"
    else
        fail "(c) unexpected spawn_insights line in actions.jsonl: ${s} (log: $(cat "${ACTIONS_LOG}" 2>/dev/null || echo '<missing>'))"
    fi

    teardown
}

# ---------------------------------------------------------------------------
# (d) lockfile held → no spawn, declined row
# ---------------------------------------------------------------------------

test_lockfile_held_no_spawn() {
    setup
    write_growth 3
    write_insights_fresh

    # Pre-create the lockfile directory (simulating a held lock)
    mkdir -p "${INSIGHTS_LOCK}"

    run_facts

    local n
    n="$(count_in "${CLAUDE_ARGV_LOG}" "/meta-insights")"
    if [ "${n}" = "0" ]; then
        pass "(d) lockfile held → no claude spawn"
    else
        fail "(d) expected no spawn with lockfile held, got: ${n}"
    fi

    local declined
    declined="$(count_in "${ACTIONS_LOG}" '"action":"spawn_insights","outcome":"declined","reason":"lockfile_held"')"
    if [ "${declined}" -ge "1" ] 2>/dev/null; then
        pass "(d) actions.jsonl contains lockfile_held declined record"
    else
        fail "(d) missing lockfile_held declined record in actions.jsonl (log: $(cat "${ACTIONS_LOG}" 2>/dev/null || echo '<missing>'))"
    fi

    rmdir "${INSIGHTS_LOCK}" 2>/dev/null || true
    teardown
}

# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

test_trigger_spawns_once
test_second_run_same_day_no_spawn
test_no_trigger_no_spawn
test_lockfile_held_no_spawn

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
if [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
exit 0
