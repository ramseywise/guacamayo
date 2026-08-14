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
   python3 ~/.claude/scripts/insights.py --output ~/workspace/guacamayo/.sounding/insights/insights-report-$(date +%F).html
   ```
   Dated filename, in `.sounding/insights/` beside `insights-log.md` — reports accumulate
   there. Then repoint the stable alias:
   ```
   ln -sf insights-report-$(date +%F).html ~/workspace/guacamayo/.sounding/insights/insights-report.html
   ```
   For dry-run: `python3 ~/.claude/scripts/insights.py --dry-run`

4. Once complete (non-dry-run), open the report:
   ```
   open ~/workspace/guacamayo/.sounding/insights/insights-report.html
   ```

5. **Summary** — present the headline numbers:
   - Sessions analyzed, date range, messages
   - % of usage over 150k context (the top cost lever)
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
   - Bash antipatterns per session (shell used where dedicated tools exist)
   - Hook blocks (PreToolUse blocks, Stop blocks) — useful vs. false-positive
   - read:edit ratio (sessions editing without reading first)
   - Long sessions without planning structure
   - **Friction label count** and content summary (from `FRICTION:` prefixes in user messages)
   - **Execution skill compliance rate** (% of execution-intent sessions invoking ≥1 skill)
   - **Spawned-agent-type distribution** (from parent Agent tool calls — compare to cost attribution)

   **Failure attribution** — classify each error event using this lookup table.
   The parser emits `tool_errors` as counts by error name with no retry-sequence data,
   so `transient` vs `code` cannot be distinguished at the signal level; merge them
   into `code (retry unknown)` for v1 and note the limitation.

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

   Note: `spec` errors (correct execution, wrong outcome) are deferred to v2 — they
   require session-level success detection not yet present in the parser output.

   Unclassified errors (no signal combination matches) → report as `unknown`; do not
   force-fit. A high `unknown` rate means the lookup table needs expansion.

   Emit a table:
   | Category | Count | % of errors | Example |
   |----------|-------|-------------|---------|
   | code     | N     | N%          | [error name] in [tool] |
   | env      | N     | N%          | ... |
   | tool     | N     | N%          | ... |
   | unknown  | N     | N%          | ... |

   Then: 1-2 sentence remediation note per non-zero category (skip `unknown` — flag it
   instead as a taxonomy gap). `env` errors → infrastructure/config action; `tool` errors
   → hook or MCP config action; `code` errors → skill/hook/workflow action.

10. **Experiment check** — read `~/workspace/guacamayo/.sounding/tooling-ledger.md`
    (active hypotheses; graduated rows in `tooling-ledger-log.md`). For each `hypothesis`
    row with a typed Metric (not `—`), check
    the session data against the metric:
    - `absence:<signal>` — search sessions for the signal; 0 occurrences = confirmed
    - `count-drop:<signal>` — count occurrences per session, compare to threshold
    - `presence:<signal>` — search for the signal; any occurrence = confirmed
    - `ratio:<metric>` — compute from session stats

    Also check legacy hypothesis rows (Metric = `—`) if their status text contains a
    checkable signal (e.g., ">150k share", "dispatch correctly").

    Report a table:
    ```
    | Experiment | Metric | Verdict | Evidence |
    ```
    Verdicts: `confirmed` (met threshold), `trending` (improving but not met),
    `inconclusive` (insufficient data), `failed` (metric violated).

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
    `~/workspace/guacamayo/.sounding/insights-log.md` (append a new dated section at the top — do NOT overwrite):

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

    ## Experiment Verdicts
    [the experiment table from step 10]

    ## Failure Attribution
    [category table from Step 9 — counts, %, top example per category]
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
