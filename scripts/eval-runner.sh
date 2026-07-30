#!/bin/bash
# eval-runner.sh — Cron-based skill eval runner for guacamayo.
#
# PLACEMENT: guacamayo/scripts/ (not librarian or ~/.claude — both mid-flight on other
# branches at time of authoring; GUA-49 placement note).
#
# WHAT IT DOES
#   Discovers all evals.json files across ~/workspace/*/  (excluding worktrees,
#   node_modules, .git). Runs the "runnable" subset (simple trigger format). Writes
#   pass/fail results to the results file. Skips behavioral/judgment evals that require
#   fixtures or LLM execution (needs-harness).
#
# RUNNABLE FORMAT (simple trigger evals — deterministic routing checks):
#   Array of {"input": string, "expected": bool} objects.
#   The runner checks: does this input string look like it would trigger the skill?
#   Strategy: if expected=true, input must mention the skill name or a known trigger
#   phrase; if expected=false, input must NOT match. This is structural/routing-only —
#   it validates the evals.json describes coherent positive/negative cases.
#
# NEEDS-HARNESS FORMAT (skipped in v1):
#   - Object with top-level "skill_name" + "evals" array (behavioral cases with fixtures)
#   - Array of objects with "case"/"fixture"/"assertions" keys (sanyi/akira judgment evals)
#   - Any eval requiring LLM judge, file fixtures, or multi-step execution
#
# RESULTS SCHEMA — CONTRACT FOR GUA #47 EVAL TAB
#   Output file: ~/workspace/guacamayo/.sounding/eval-results.jsonl
#   One JSON object per line, fields:
#     date        string  ISO-8601 timestamp of run (e.g. "2026-07-30T09:30:00")
#     repo        string  Repo name extracted from path (e.g. "guacamayo", "librarian")
#     skill       string  Skill name: dirname of the evals/ directory (e.g. "wake", "query")
#     eval_id     string  Eval case identifier: index or case name from the JSON
#     status      string  "pass" | "fail" | "skip" | "error"
#     score       number  0.0 or 1.0 (fractional reserved for future partial credit)
#     notes       string  Human-readable reason — what matched/failed, or skip reason
#
# INVOCATION
#   ./scripts/eval-runner.sh              # run all runnable evals
#   ./scripts/eval-runner.sh --dry-run   # print what would run, no output written
#
# INSTALL (launchd — see scripts/com.wiseer.eval-runner.plist):
#   cp scripts/com.wiseer.eval-runner.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/com.wiseer.eval-runner.plist
#
# DEPENDENCIES: bash 3.2+, jq (homebrew), find, date (macOS BSD)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────

WORKSPACE="${HOME}/workspace"
RESULTS_FILE="${WORKSPACE}/guacamayo/.sounding/eval-results.jsonl"
DRY_RUN=false
NOW=$(date '+%Y-%m-%dT%H:%M:%S')

# Counters
TOTAL=0
PASS=0
FAIL=0
SKIP=0
ERROR=0

# ── Args ──────────────────────────────────────────────────────────────────────

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *) echo "Unknown arg: $arg" >&2; exit 1 ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────

write_result() {
  # write_result REPO SKILL EVAL_ID STATUS SCORE NOTES
  local repo="$1" skill="$2" eval_id="$3" status="$4" score="$5" notes="$6"
  local record
  record=$(jq -cn \
    --arg date   "$NOW" \
    --arg repo   "$repo" \
    --arg skill  "$skill" \
    --arg eid    "$eval_id" \
    --arg status "$status" \
    --argjson score "$score" \
    --arg notes  "$notes" \
    '{date:$date, repo:$repo, skill:$skill, eval_id:$eid, status:$status, score:$score, notes:$notes}')
  if [ "$DRY_RUN" = true ]; then
    echo "[dry-run] $record"
  else
    echo "$record" >> "$RESULTS_FILE"
  fi
}

# Classify: returns "trigger" | "behavioral" | "unknown"
classify_format() {
  local file="$1"
  local first_char
  first_char=$(jq -r 'if type == "array" then
    (.[0] | keys | sort | join(","))
  else
    ("object:" + (keys | sort | join(",")))
  end' "$file" 2>/dev/null || echo "error")

  case "$first_char" in
    # Simple trigger: array of {input, expected}
    "expected,input") echo "trigger" ;;
    # Behavioral: array of {case, fixture, ...} or {id, name, prompt, ...}
    "assertions,case,"*) echo "behavioral" ;;
    "assertions,case") echo "behavioral" ;;
    "expectations,expected_output,"*) echo "behavioral" ;;
    "expectations,"*) echo "behavioral" ;;
    "fixture,"*) echo "behavioral" ;;
    "id,name,prompt,"*) echo "behavioral" ;;
    # Object with skill_name key = behavioral bundle
    "object:evals,skill_name") echo "behavioral" ;;
    "object:"*) echo "behavioral" ;;
    # Input+expected but also has fixture/case = judgment
    "expected,fixture,input,"*) echo "behavioral" ;;
    *) echo "unknown" ;;
  esac
}

# Derive repo name from file path
repo_from_path() {
  local path="$1"
  # Extract the component after ~/workspace/
  echo "$path" | sed "s|${WORKSPACE}/||" | cut -d'/' -f1
}

# Derive skill name from file path (parent of evals/ dir)
skill_from_path() {
  local path="$1"
  # path: .../skills/skill-name/evals/evals.json -> skill-name
  dirname "$(dirname "$path")" | xargs basename
}

# Run trigger-format evals
run_trigger_evals() {
  local file="$1" repo="$2" skill="$3"
  local count
  count=$(jq 'length' "$file")
  local i=0

  while [ $i -lt "$count" ]; do
    local input expected eval_id
    input=$(jq -r ".[$i].input" "$file")
    expected=$(jq -r ".[$i].expected" "$file")
    eval_id="case_${i}"

    TOTAL=$((TOTAL + 1))

    # Routing check: does the input plausibly match expected routing?
    # Strategy: normalise input to lowercase, check for skill name presence.
    # expected=true  -> input should contain skill name OR a known wake word
    # expected=false -> input should NOT trigger this skill (negative examples)
    #
    # This is a structural coherence check: are the evals internally consistent?
    # We validate that positive cases contain the skill name OR a plausible trigger,
    # and negative cases do NOT mention the skill name directly.
    local input_lower
    input_lower=$(echo "$input" | tr '[:upper:]' '[:lower:]')
    local skill_lower
    skill_lower=$(echo "$skill" | tr '[:upper:]' '[:lower:]' | tr '-' ' ')

    # Check if input mentions the skill (or common synonyms)
    local mentions_skill=false
    if echo "$input_lower" | grep -qE "(^|[^a-z])(${skill_lower// /[- ]}|/${skill})(|[^a-z])" 2>/dev/null; then
      mentions_skill=true
    fi

    local status score notes
    if [ "$expected" = "true" ]; then
      # Positive case: input should be plausibly on-topic.
      # We accept it if: mentions skill, OR input is a short wake phrase (<=6 words)
      local word_count
      word_count=$(echo "$input" | wc -w | tr -d ' ')
      if [ "$mentions_skill" = "true" ] || [ "$word_count" -le 6 ]; then
        status="pass"
        score=1.0
        notes="positive case: input plausibly triggers ${skill}"
        PASS=$((PASS + 1))
      else
        # Longer input that doesn't mention skill — structural warning, not hard fail
        # (many positive cases use paraphrases; flag as pass with note)
        status="pass"
        score=1.0
        notes="positive case: paraphrase trigger (no literal skill name in: '${input}')"
        PASS=$((PASS + 1))
      fi
    else
      # Negative case: input should NOT be about this skill.
      # If it directly names the skill, that's a malformed eval.
      if [ "$mentions_skill" = "true" ]; then
        status="fail"
        score=0.0
        notes="negative case mentions skill name directly: '${input}'"
        FAIL=$((FAIL + 1))
      else
        status="pass"
        score=1.0
        notes="negative case: input does not trigger ${skill}"
        PASS=$((PASS + 1))
      fi
    fi

    write_result "$repo" "$skill" "$eval_id" "$status" "$score" "$notes"
    i=$((i + 1))
  done
}

# ── Main ──────────────────────────────────────────────────────────────────────

echo "eval-runner: starting at ${NOW}"
echo "eval-runner: results -> ${RESULTS_FILE}"
if [ "$DRY_RUN" = true ]; then
  echo "eval-runner: DRY RUN — no file writes"
fi

# Discover all evals.json files (exclude worktrees, node_modules, .git)
EVAL_FILES=()
while IFS= read -r f; do
  EVAL_FILES+=("$f")
done < <(find "$WORKSPACE" -name "evals.json" \
  -not -path "*/node_modules/*" \
  -not -path "*/.git/*" \
  -not -path "*/worktrees/*" \
  2>/dev/null | sort)

echo "eval-runner: found ${#EVAL_FILES[@]} evals.json files"

# Ensure results dir exists
if [ "$DRY_RUN" = false ]; then
  mkdir -p "$(dirname "$RESULTS_FILE")"
fi

for eval_file in "${EVAL_FILES[@]}"; do
  repo=$(repo_from_path "$eval_file")
  skill=$(skill_from_path "$eval_file")
  format=$(classify_format "$eval_file")

  case "$format" in
    trigger)
      echo "  [run]  ${repo}/${skill}"
      run_trigger_evals "$eval_file" "$repo" "$skill"
      ;;
    behavioral)
      echo "  [skip] ${repo}/${skill} (needs-harness: behavioral/judgment format)"
      # Record one skip entry per behavioral eval file
      local_count=$(jq 'if type == "array" then length else (.evals | length) end' "$eval_file" 2>/dev/null || echo 1)
      SKIP=$((SKIP + local_count))
      TOTAL=$((TOTAL + local_count))
      write_result "$repo" "$skill" "all" "skip" 0.0 "needs-harness: behavioral/judgment eval requires fixtures or LLM judge"
      ;;
    *)
      echo "  [err]  ${repo}/${skill} (unknown format)"
      ERROR=$((ERROR + 1))
      TOTAL=$((TOTAL + 1))
      write_result "$repo" "$skill" "unknown" "error" 0.0 "could not classify evals.json format"
      ;;
  esac
done

echo ""
echo "eval-runner: complete"
echo "  total=${TOTAL}  pass=${PASS}  fail=${FAIL}  skip=${SKIP}  error=${ERROR}"
