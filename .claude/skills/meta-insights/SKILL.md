---
name: meta-insights
description: "Generate a Claude Code usage insights report from session history — token economics, context health, friction patterns, experiment verdicts. Trigger on: /meta-insights, 'insights', 'usage report', 'session insights'. Output feeds /meta-retro Step 1."
allowed-tools: Read Write Edit Bash Glob
---

# Claude Code Insights

Analyze all Claude Code sessions and generate a report covering:
- Token economics: cost by model, by tool, by skill/agent, context-size distribution
- Context load: what contributes to context growth (skills, hooks, always-loaded files)
- Friction patterns: antipatterns, errors, hook blocks
- Experiment verdicts: check active hypotheses from the tooling ledger
- Recommendations: concrete changes ranked by impact

The engine is `librarian/tools/cartographer/parser.py` (canonical since 2026-07-17).
`~/.claude/scripts/insights.py` is a forwarding shim to it — same flags either way.

## Steps

1. Load the `insights-analysis` ref (`~/.claude/refs/insights-analysis.md`) — use
   this as the interpretation framework when reviewing the generated report with the user.

2. Check that `ANTHROPIC_API_KEY` is set in the environment (or `~/.claude/.env` — the parser
   falls back to it). If neither, tell the user and offer `--dry-run` (keyless stats only).

3. Run the insights engine:
   ```
   python3 ~/.claude/scripts/insights.py --output ~/workspace/guacamayo/.sounding/insights/insights-report.html
   ```
   **Pass the bare filename — do not date it here.** `librarian/shared/parser.py:1377` appends
   today's date to the stem itself and then symlinks the name you passed to the dated file
   (`parser.py:1450-1453`), so a dated argument yields
   `insights-report-2026-08-14-2026-08-14.html` — a doubling already visible in
   `.sounding/insights/`. Reports accumulate there beside `insights-log.md`, and
   `insights-report.html` is repointed by the parser — no manual `ln -sf` step.

   For dry-run: `python3 ~/.claude/scripts/insights.py --dry-run`

4. Once complete (non-dry-run), open the report:
   ```
   open ~/workspace/guacamayo/.sounding/insights/insights-report.html
   ```

4b. **Session count verification** — before computing any per-session ratio, cross-check
   the session count against the factstore:
   ```
   sqlite3 ~/workspace/librarian/data/sessions.db "SELECT COUNT(*) FROM sessions WHERE date >= '<start-date>';"
   ```
   The insights engine and the factstore must agree on session count for the same date
   range. A divergence (feedback-log 2026-08-20, C1: 382 vs 416 for the same window)
   means one source is filtering differently — diagnose before reporting ratios, because
   every per-session metric inherits the denominator error.

5. **Summary** — present the headline numbers:
   - Sessions analyzed, date range, messages
   - % of **sessions** over 150k context (the top cost lever) — this is
     `COUNT(sessions > 150k) / COUNT(all sessions)`, NOT the cost share in those sessions.
     The dashboard computes both (`pct_over_150k` = session count ratio,
     `cost_bucket_pct_over150k` = cost share). Never conflate them — the cost share is
     always higher because expensive sessions are expensive. Feedback-log 2026-08-20 C3
     found 19% stated vs 5% measured — a 3.8× overstatement from mixing the two.
   - Cache hit rate and savings
   - Subagent share

6. **Model breakdown** — from `model_distribution`, report cost-weighted usage per model.
   Flag if expensive models (opus) are used on routine tasks, or cheap models on
   judgment-dense work. Compare to the model-pairing ref (`~/.claude/refs/models.md`).

7. **Tool & skill economics** — from `top_tools`, `skill_usage_pct`, `skill_invocations`:
   - Which tools dominate (Read/Edit/Bash) and their relative share
   - Which skills consume the most context (by `skill_usage_pct` — cost-weighted)
   - Skill invocation frequency vs cost share (high-freq/low-cost = efficient; low-freq/high-cost = bloated)
   - Agent spawns: count, model used, share of total spend
   - Flag skills/agents that load disproportionate context per invocation

   **Coverage diff** — `skill_invocations` only shows what ran. Also report what never
   did, by diffing invoked names against skills on disk. Pass the `skill_invocations`
   dict from the step-3 run (do not re-run the parser):

   ```
   python3 - <<'PY'
   import json,os,glob
   si = json.loads(os.environ['SKILL_INVOCATIONS'])   # from the step-3 output
   g={os.path.basename(p.rstrip('/')) for p in glob.glob(os.path.expanduser('~/.claude/skills/*/'))}
   r={}
   for p in glob.glob(os.path.expanduser('~/workspace/*/.claude/skills/*/')):
       n=os.path.basename(p.rstrip('/'))
       r.setdefault(n,[]).append(p.split('/workspace/')[1].split('/')[0])
   print('GLOBAL NEVER INVOKED:',sorted(g-set(si)))
   print('REPO NEVER INVOKED:',sorted(f'{s} ({",".join(r[s])})' for s in set(r)-set(si)))
   print('INVOKED, NOT ON DISK:',sorted(set(si)-(g|set(r))))
   PY
   ```

   Read the three lists with these caveats — do NOT report raw counts as fact:

   - **Zero invocations ≠ unused.** `skill_invocations` merges two sources
     (`parser.py:307`): typed `/slash` text, plus `Skill` tool calls. That covers both
     direct and auto-triggered use, but a skill whose logic was inlined by hand — the work
     done without ever invoking it — still reads as zero. Treat the zero set as a
     description-quality signal, not a delete list.
   - **"Invoked, not on disk" is mostly noise**: built-in CLI commands (`/clear`,
     `/config`, `/compact`), bare paths (`/private`, `/tmp`), and typos. Two things there
     are real and worth flagging: a **typo'd invocation** that silently did nothing (e.g.
     `design-inistiative`), and a **name that looks like a skill you meant to have**.
   - Repo skills are only reachable from their own repo. Weight a repo skill's zero count
     against how often you work in that repo before calling it dead.

   Report the zero-invocation set as a **candidate list for description review**
   (`skill-creator` has description-optimization), not as dead weight. Recommend deletion
   only where a skill is both never invoked AND superseded by a named alternative.

8. **Context load analysis** — what contributes to context growth:
   - Always-loaded files (CLAUDE.md chain, rules, MEMORY.md) — estimate token count
   - Per-skill context additions (skill prompt size + files read during skill)
   - Hook overhead (number of hooks × fire frequency)
   - Recommend: which skills/hooks/always-loaded content to slim or lazy-load

9. **Friction patterns** — from tool errors, bash antipatterns, hook blocks, and
   explicit user signals:
   - Error types and frequency
   - Bash antipatterns **median (p50)** per session — this signal is a MEDIAN, not a
     mean. Always say "median" in the report, never "average" or "per-session average".
     The resolver (`_bash_antipatterns_p50`) computes p50. Feedback-log 2026-08-20 C2
     found the prose said "average" while the number was a median — 3-point gap.
   - Hook blocks (PreToolUse blocks, Stop blocks) — useful vs. false-positive
   - read:edit ratio (sessions editing without reading first)
   - Long sessions without planning structure
   - **Friction label count** and content summary (from `FRICTION:` prefixes in user messages)
   - **Execution skill compliance rate** (% of execution-intent sessions invoking ≥1
     **guardrail** skill — only workflow-execute/review, code-review/debug/refactor count.
     Identity skills like wake/grow/dream do NOT count as execution compliance.
     Feedback-log 2026-08-20 C5 found counting all skills inflated this 7× (36% vs 4.9%)
   - **Spawned-agent-type distribution** (from parent Agent tool calls — compare to cost attribution)

   **Failure attribution** — do NOT classify error events by hand. Attribution is
   computed at parse time (LIB-57) into five per-session columns on the `sessions`
   table of the cartographer factstore: `errors_code`, `errors_env`, `errors_tool`,
   `errors_unknown`, `bash_antipatterns` (`librarian/tools/cartographer/factstore.py:118-122`,
   written at `factstore.py:759-763`). `errors_code + errors_env + errors_tool +
   errors_unknown` sums to `tool_error_count`; `bash_antipatterns` mirrors the parser's
   own per-session count.

   Read them by summing, against the factstore (default
   `~/workspace/librarian/data/sessions.db`, `--store` in cartographer):

   ```
   sqlite3 -header ~/workspace/librarian/data/sessions.db "
     SELECT SUM(errors_code) AS code, SUM(errors_env) AS env,
            SUM(errors_tool) AS tool, SUM(errors_unknown) AS unknown,
            SUM(bash_antipatterns) AS bash_antipatterns
     FROM sessions;"
   ```

   Add a `WHERE date >= '<YYYY-MM-DD>'` clause to scope to the reporting window.

   Classification happens at parse time by necessity, not preference: the parser
   reduces raw `tool_result` error text to an error-kind count dict and discards the
   text, so attribution cannot be recovered post-hoc from an existing row. Backfill
   requires re-parsing retained JSONL (~15-day retention ceiling) — sessions older than
   that carry NULL/0 in these columns rather than a real zero. Say so when the window
   reaches back further than retention.

   *Reference — how the columns are computed.* This table documents the parse-time
   classification; it is NOT a procedure to run. Do not re-derive categories from it.

   | Signal combination | Category | Code |
   |--------------------|----------|------|
   | Hook block (`user_rejected` error on any tool) | tool | `tool` |
   | `permission_denied` + not a hook block | env | `env` |
   | `command_failed` | code | `code` (retry unknown — parser carries no retry sequence) |
   | `file_not_found` | code | `code` (retry unknown) |
   | `file_too_large` | env | `env` |
   | `edit_failed` | code | `code` |
   | Quota / rate-limit message in error text | env | `env` |
   | `other` | unknown | `unknown` |

   Two limitations still hold and should be noted in the report: `transient` vs `code`
   is indistinguishable (the parser carries no retry sequence, so both land in
   `errors_code`), and `spec` errors (correct execution, wrong outcome) are not
   classified at all — they need session-level success detection the parser does not
   emit. Unrecognised error kinds fall to `errors_unknown` rather than being force-fit
   (`factstore.py:208`); a high `unknown` share means the parse-time taxonomy needs
   expansion — report it as a taxonomy gap, and fix it in the parser, not here.

   Emit a table:
   | Category | Count | % of errors | Example |
   |----------|-------|-------------|---------|
   | code     | N     | N%          | [error name] in [tool] |
   | env      | N     | N%          | ... |
   | tool     | N     | N%          | ... |
   | unknown  | N     | N%          | ... |

   The `Example` column is not in the columns — the per-session counts carry no
   exemplar. Pull examples from the run's `tool_errors` breakdown, or leave the column
   as `—`; never invent one.

   Then: 1-2 sentence remediation note per non-zero category (skip `unknown` — flag it
   instead as a taxonomy gap). `env` errors → infrastructure/config action; `tool` errors
   → hook or MCP config action; `code` errors → skill/hook/workflow action.

10. **Experiment check** — do NOT compute verdicts by hand. Scoring is deterministic
    and already done: `librarian/tools/cartographer/verdicts.py` owns the arithmetic,
    and each cartographer run appends one row per ledger experiment to the
    `experiment_verdicts` table (`factstore.py:615-620`, appended at
    `factstore.append_verdicts:657`, wired in `__main__.py:309-330`). Columns:
    `experiment`, `date`, `metric`, `verdict`, `evidence`, plus `run_at`.

    The table is append-only — PK `(experiment, date, run_at)` — so it carries verdict
    *trajectory* across runs. `date` is the ledger hypothesis date, NOT the run date.
    Query the latest `run_at` per `(experiment, date)`:

    ```
    sqlite3 -header ~/workspace/librarian/data/sessions.db "
      SELECT v.experiment, v.date, v.metric, v.verdict, v.evidence
      FROM experiment_verdicts v
      JOIN (SELECT experiment, date, MAX(run_at) AS run_at
            FROM experiment_verdicts GROUP BY experiment, date) latest
        ON v.experiment = latest.experiment
       AND v.date       = latest.date
       AND v.run_at     = latest.run_at
      ORDER BY v.date DESC;"
    ```

    Your job is interpretation, not measurement. Report the table as-is:
    ```
    | Experiment | Metric | Verdict | Evidence |
    ```
    Verdicts: `confirmed` (met threshold), `trending` (improving but not met),
    `inconclusive` (insufficient data), `failed` (metric violated).

    **Read `inconclusive` correctly — it is the common case, and it is not a data
    shortage.** Signal → measurement is a closed registry (`verdicts.py:229-235`),
    currently five signals: `bash-antipatterns`, `p90-output-tokens`,
    `execution-sessions-with-skills`, `top-session-cost-concentration`,
    `fable-tokens-in-non-verdict-skills`. Ledger signals naming process/textual events
    (e.g. `worktree-commit-blocks`, `flat-sibling-issues-without-parent-link`) have no
    factstore column and score `inconclusive` with evidence saying exactly that —
    deliberately, so an unobservable `absence:` claim never reads as a false
    `confirmed`. Do not "resolve" those rows by searching sessions yourself; surface
    them as **unmeasurable-by-construction** and, if a signal is worth measuring, the
    fix is a new entry in `_SIGNAL_METRICS`, not a hand-derived verdict here.

    Two further notes: legacy rows with Metric `—` score `inconclusive` ("no typed
    metric to score") — `verdicts.py` does not attempt the prose heuristic, and neither
    should you. A row with multiple metric clauses (joined by ` + `) is scored
    pessimistically — the worst clause wins.

    If the table is empty or stale, the cartographer run was skipped or `--no-verdicts`
    was passed; re-run it rather than falling back to hand-scoring.

    Do NOT update the ledger — that's /retro's job. Just surface the verdicts.

11. **Recommendations** — synthesize findings into 3-5 ranked recommendations:
    ```
    ### R<N>: <one-line recommendation>
    **Impact**: <which metric this moves and by how much>
    **Mechanism**: <what to change — hook, skill, setting, workflow>
    **Metric**: <how to measure success — typed metric for the ledger>
    ```
    Rank by cost-weighted impact. The single biggest lever goes first.

12. **Persist summary** — write the machine-readable output to
    `~/workspace/guacamayo/.sounding/insights/insights-log.md` (append a new dated section at the top — do NOT overwrite):

    ```markdown
    # Insights Summary — [date]

    ## Numbers
    [key metrics as a table]

    ## Model Distribution
    [model: message count, cost-weight share]

    ## Skill Economics
    [skill: invocations, cost-weight share, context contribution]

    ## Skill Coverage
    [never-explicitly-invoked: global list, repo list (with repo names)]
    [typo'd/unresolved invocations worth fixing]

    ## Skill Candidate Patterns

    [Threshold: 3 sessions, min sequence length: 3, max: 5]
    [Execution sessions analyzed: N (intent=execution, Skill=0, tool_sequence non-NULL)]
    [Sessions excluded (meta/unlabelled/pre-migration): M]

    Run the detector (sessions = rows from sessions.db via `SELECT session_id, session_intent,
    tool_counts, tool_sequence FROM sessions`):
    ```python
    from telemetry.skill_candidates import detect_skill_candidates
    patterns = detect_skill_candidates(sessions)
    ```

    For each pattern crossing the threshold, emit:

    ### Candidate: [tool1→tool2→...→toolN] (n=N)
    - Count: K sessions
    - Sessions: [id1, id2, ...]

    If no patterns crossed the threshold: `[No patterns found above threshold=3 in this window]`

    If `tool_sequence` is NULL for all sessions in the window (pre-LIB-125 migration):
    `[Skill candidate detection skipped — tool_sequence column not yet populated (pre-migration)]`

    Note: session IDs are the stable cross-reference to JSONL; /meta-retro Step 1.5
    uses them to sample sessions for spot-checking. Do not substitute session dates.

    ## Experiment Verdicts
    [the experiment table from step 10]

    ## Failure Attribution
    [category table from Step 9 — counts and %, summed from the errors_* columns;
     example per category only where the run's tool_errors breakdown supplies one]
    [remediation notes per non-zero non-unknown category]
    [flag: transient vs code indistinguishable until parser emits retry sequences]

    ## Recommendations
    [the ranked recommendations from step 11]

    ## Trends
    [comparison to previous run if prior summary exists — what improved, what worsened]
    ```

    This file is what `/retro` reads as an observation source (Step 1.1 in retro).

13. **Dashboard refresh (if asked)** — chart/panel updates go to
    `~/workspace/guacamayo/.sounding/context-dashboard.html`, the meta-wake/meta-grow/meta-dream shared
    artifact (also the pulse.sh target). Never create or write
    `~/workspace/guacamayo/.sounding/dashboard.html` — that is a deprecated pre-rename
    path; old plan docs (GUA-43/44/45, context-engineering-v2) still mention it, ignore
    them on this point.

## Options

Arguments pass through to the engine:

- `--dry-run` — extract stats only, no API call, print JSON to stdout
- `--model claude-sonnet-5` — report-generation model
- `--output <path>` — report path. Always pass it explicitly (step 3) — reports live in
  `~/workspace/guacamayo/.sounding/insights/`, never at `.sounding/` root
- `--sessions-dir <path>` — session-note markdown files (default `~/.claude/sessions`)
- `--projects-dir <path>` — JSONL location (default `~/.claude/projects`)

Cartographer-only subcommands (run from librarian): `--cron`, `--migrate`, `--compare`, `--enrich`.
