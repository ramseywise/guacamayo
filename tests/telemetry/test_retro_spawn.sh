#!/usr/bin/env bash
# tests/telemetry/test_retro_spawn.sh — Shell-level tests for Step 7 retro spawn.
#
# Tests:
#   (a) due state (retro_due > retro_acked) → exactly one spawn
#   (b) second run same day → no spawn (stamp guard)
#   (c) retro_due == retro_acked → no spawn
#   (d) lockfile held → no spawn
#
# The stub `claude` records its argv to a file; we assert on it.
# Run: bash tests/telemetry/test_retro_spawn.sh

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
CASCADE_STATE=""
ACTIONS_LOG=""
RETRO_LOCK=""
RETRO_STAMP_DIR=""
CLAUDE_ARGV_LOG=""
CLAUDE_BIN=""

setup() {
    TEST_TMP="$(mktemp -d)"
    FAKE_REPO="${TEST_TMP}/repo"
    TELEMETRY_DIR="${FAKE_REPO}/.sounding/telemetry"
    CASCADE_STATE="${TELEMETRY_DIR}/cascade-state.json"
    ACTIONS_LOG="${TELEMETRY_DIR}/actions.jsonl"
    RETRO_LOCK="${TELEMETRY_DIR}/retro-spawn.lock"
    RETRO_STAMP_DIR="${TELEMETRY_DIR}/stamps"
    CLAUDE_ARGV_LOG="${TEST_TMP}/claude-argv.log"
    CLAUDE_BIN="${TEST_TMP}/bin"

    mkdir -p "${FAKE_REPO}/logs"
    mkdir -p "${RETRO_STAMP_DIR}"
    mkdir -p "${CLAUDE_BIN}"
    touch "${CLAUDE_ARGV_LOG}"

    # Stub: claude records argv, exits 0
    cat > "${CLAUDE_BIN}/claude" <<EOF
#!/usr/bin/env bash
echo "\$@" >> "${CLAUDE_ARGV_LOG}"
exit 0
EOF
    chmod +x "${CLAUDE_BIN}/claude"

    # Stub: uv exits 0 (board tick)
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

write_state() {
    local due="$1" acked="$2"
    printf '{"compacts":1,"grows_due":0,"insights_due":0,"retro_due":%d,"retro_acked":%d}\n' \
        "${due}" "${acked}" > "${CASCADE_STATE}"
}

run_board() {
    # TELEMETRY_CRON_REPO_DIR overrides REPO_DIR inside the script.
    TELEMETRY_CRON_REPO_DIR="${FAKE_REPO}" \
    PATH="${CLAUDE_BIN}:${PATH}" \
        bash "${SCRIPT}" board 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# (a) due state → exactly one spawn
# ---------------------------------------------------------------------------

test_due_spawns_once() {
    setup
    write_state 2 1   # retro_due=2 > retro_acked=1

    run_board

    local n
    n="$(count_in "${CLAUDE_ARGV_LOG}" "/meta-retro")"
    if [ "${n}" = "1" ]; then
        pass "(a) due state spawns exactly once (claude calls=${n})"
    else
        fail "(a) expected 1 claude call, got: ${n}"
    fi

    local a
    a="$(count_in "${ACTIONS_LOG}" '"outcome":"acted"')"
    if [ "${a}" = "1" ]; then
        pass "(a) actions.jsonl has 1 acted spawn_retro"
    else
        fail "(a) expected 1 acted spawn_retro in actions.jsonl, got: ${a} (log: $(cat "${ACTIONS_LOG}" 2>/dev/null || echo '<missing>'))"
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
# (b) second run same day → no second spawn (stamp guard)
# ---------------------------------------------------------------------------

test_second_run_same_day_no_spawn() {
    setup
    write_state 2 1

    # First run — populates stamp
    run_board

    # Reset argv log; keep stamp and actions log
    printf '' > "${CLAUDE_ARGV_LOG}"

    # Second run same day — stamp is already present
    run_board

    local n
    n="$(count_in "${CLAUDE_ARGV_LOG}" "/meta-retro")"
    if [ "${n}" = "0" ]; then
        pass "(b) second run same day produced no claude spawn"
    else
        fail "(b) expected 0 claude calls on second run, got: ${n}"
    fi

    # Confirm already_ran_today declined record
    local declined
    declined="$(count_in "${ACTIONS_LOG}" 'already_ran_today')"
    if [ "${declined}" -ge "1" ] 2>/dev/null; then
        pass "(b) actions.jsonl contains already_ran_today declined record"
    else
        fail "(b) missing already_ran_today declined record in actions.jsonl (log: $(cat "${ACTIONS_LOG}" 2>/dev/null || echo '<missing>'))"
    fi

    teardown
}

# ---------------------------------------------------------------------------
# (c) retro_due == retro_acked → no spawn
# ---------------------------------------------------------------------------

test_acked_no_spawn() {
    setup
    write_state 1 1   # equal → no spawn

    run_board

    local n
    n="$(count_in "${CLAUDE_ARGV_LOG}" "/meta-retro")"
    if [ "${n}" = "0" ]; then
        pass "(c) retro_due==retro_acked → no spawn"
    else
        fail "(c) expected no spawn when acked, got claude calls: ${n}"
    fi

    # Confirm no spawn_retro line in actions.jsonl at all
    local s
    s="$(count_in "${ACTIONS_LOG}" '"action":"spawn_retro"')"
    if [ "${s}" = "0" ]; then
        pass "(c) no spawn_retro line in actions.jsonl when acked"
    else
        fail "(c) unexpected spawn_retro line in actions.jsonl: ${s} (log: $(cat "${ACTIONS_LOG}" 2>/dev/null || echo '<missing>'))"
    fi

    teardown
}

# ---------------------------------------------------------------------------
# (d) lockfile held → no spawn
# ---------------------------------------------------------------------------

test_lockfile_held_no_spawn() {
    setup
    write_state 3 1   # clearly due

    # Pre-create the lockfile directory (simulating a held lock)
    mkdir -p "${RETRO_LOCK}"

    run_board

    local n
    n="$(count_in "${CLAUDE_ARGV_LOG}" "/meta-retro")"
    if [ "${n}" = "0" ]; then
        pass "(d) lockfile held → no claude spawn"
    else
        fail "(d) expected no spawn with lockfile held, got: ${n}"
    fi

    # Confirm lockfile_held declined record
    local declined
    declined="$(count_in "${ACTIONS_LOG}" 'lockfile_held')"
    if [ "${declined}" -ge "1" ] 2>/dev/null; then
        pass "(d) actions.jsonl contains lockfile_held declined record"
    else
        fail "(d) missing lockfile_held declined record in actions.jsonl (log: $(cat "${ACTIONS_LOG}" 2>/dev/null || echo '<missing>'))"
    fi

    rmdir "${RETRO_LOCK}" 2>/dev/null || true
    teardown
}

# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

test_due_spawns_once
test_second_run_same_day_no_spawn
test_acked_no_spawn
test_lockfile_held_no_spawn

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
if [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
exit 0
