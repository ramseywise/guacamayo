# Tooling Ledger

Every change to the tooling layer (hooks, skills, rules, settings) gets a row: what
changed, the friction that motivated it, and whether the fix actually took. `/retro`
reads this first — `hypothesis` rows are its top queue. Statuses: `hypothesis` (change
made, effect unproven) → `verified (evidence)` or `failed (evidence)`. Keep under ~1
screen: compress verified rows into monthly rollups.

## Experiment Tracking

Each `hypothesis` row carries a **Metric** — the observable signal that confirms or fails
the change. Metrics are machine-readable so `/insights` can check them against session data:

| Metric type | Format | Example |
|---|---|---|
| absence | `absence:<signal> for <N> sessions` | `absence:zsh-glob-abort for 3 sessions` |
| count-drop | `count-drop:<signal> from <N> to <M>` | `count-drop:permission-prompt from 5 to <2/session` |
| presence | `presence:<signal> within <N> sessions` | `presence:retrieval.jsonl rows within 5 sessions` |
| ratio | `ratio:<metric> <direction> <threshold>` | `ratio:>150k-context below 40%` |
| hook-blocks | `hook-blocks:<hook> <dir> <threshold>` | `hook-blocks:bash_antipattern_warn above 5/session` |

`/insights` scans active hypotheses and reports: confirmed (metric met), trending (partial),
inconclusive (insufficient data), or failed (metric violated). `/retro` Step 0 uses these
verdicts to graduate or fail rows without re-deriving evidence manually.

---

| Date | Change | Motivating friction | Metric | Status |
|---|---|---|---|---|
| 2026-07 (rollup) | Settings Bash patterns; /retro + ledger; cartographer keyless; v2→v3 lifecycle; doc-artifact collapse; akira global port; commands/ retired; wake-nudge; model pairing codified; .claude/docs/ git-ignored (5d no incident); shell.md deletion-safety (0 incidents/41 sessions); /grow broadened (4 process + 4 friction entries); experiment tracking (2 /insights runs with verdicts) | 18 items verified Jul 2026 | — | verified |
| 2026-07-17 (batch) | 12 infra changes awaiting specific trigger events: sanyi contract review, sync-global-skills detail output, zsh-gotchas (0 aborts), skill dedupe dispatch, librarian factual-record ingest, phase-protocol `repo:` scoping, rules→refs dispatch, review-sweep fresh-session akira-scan, review ladder L1-vs-L2 token comparison, retrieval telemetry accumulation, /compact-wiki first dry-run, repo-security-setup from ref | — | hypothesis (batch — verify individually on trigger) |
| 2026-07-17 | Session hygiene + context-health rule: one work item per session, plan-doc as continuity, compact at phase boundaries/30-turn heuristic | 66% of usage at >150k context | `ratio:>150k-context below 40%` | hypothesis — trending: 66%→58%→52%→42% |
| 2026-07-18 | `memory_route_guard.sh` blocks writes to global auto-memory dir | Global memory protocol wrote identity facts silently | — | hypothesis — verify: next auto-memory write blocked |
| 2026-07-19 | `task_complete_check.sh` (Stop hook): blocks completion until ruff/tsc/pytest pass | Claude finishing with lint errors or broken tests | `absence:lint-errors-on-commit for 5 sessions` | hypothesis |
| 2026-07-19 | `mcp-builder` moved refs/ → skills/ (20th global skill) | Vendored skill was inert as a ref | `presence:mcp-builder-invoked within 3 MCP sessions` | hypothesis |
| 2026-07-19 | Ledger compressed: verified→rollup, legacy batch consolidated | 21 hypothesis rows exceeded ~1 screen | `absence:ledger-over-30-lines for 3 retros` | hypothesis |
| 2026-07-19 | `/docs-check` (21st global skill) + `docs_drift_warn.sh` hook | No mechanism detected doc-vs-code drift | `presence:docs-check-finding within 3 L2 reviews` | hypothesis |
| 2026-07-20 | `/sanyi init` step 2: verify candidates against implementation before writing | SANYI.md v1 was false on arrival — guardrails had zero call sites | `absence:contract-entry-with-zero-callsites for 2 inits` | hypothesis |
| 2026-07-20 | Plan-doc outcome metric: ABANDONED status exists but never used | 0/37 plan docs say ABANDONED; success ratio = 100% by construction | `presence:abandoned-status-used within 3 abandoned plans` | hypothesis |
| 2026-07-20 | `bash_antipattern_warn.sh`: advisory (exit 0) → **blocking** (exit 2) for standalone cat/grep/find; pipes still allowed | Advisory failed: antipatterns 25.8→27.85/session (UP). PreToolUse advisory is structurally ineffective — model has already committed to Bash | `count-drop:bash-antipatterns from 28 to <15/session` | hypothesis (replaces failed advisory) |
| 2026-07-20 | Spawn prompt model guidance in CLAUDE.md session hygiene: `--model sonnet` for impl, opus for meta. "Read files before editing" in subagent instructions | 100% opus on 41 spawned sessions; read:edit 0.96, 77/139 below 1.0 | `ratio:opus-share below 35%` | hypothesis |
| 2026-07-20 | Skill name mismatches fixed (5 repos: underscore→hyphen in frontmatter); typo aliases added to workflow-research and design-initiative descriptions | 5 skills with name mismatch broke /slash dispatch; `reserach` (5×) and `design-inistiative` (1×) failed silently | `absence:skill-name-mismatch for 2 retros` | hypothesis |
| 2026-07-20 | listen-wiseer `code-refactor` duplicate deleted (global is canonical) | Config-layering violation: same skill in repo AND global | `absence:duplicate-skill-names for 3 retros` | hypothesis |
| 2026-07-20 | `growth-log.md` ledger + dream Phase 7c-bis + `dream-ledger-gate.sh` blocking hook | F8/F15: identity revision destroys its own evidence; identity layer has no review gate | `presence: growth-log.md row count >= entries cleared, checked at each /dream` | hypothesis — verdict due 2026-08-03 |
| 2026-07-20 | gh-7: Hook telemetry — log_event() in lib.sh; blocking hooks log to .hook-log.jsonl; advisory hooks log on warn; pip/destructive_cmd extracted to scripts; cartographer parse_hook_log() emits hook_telemetry in --dry-run; hook-blocks metric type in ledger | No per-hook telemetry; aggregate hook_blocks_total unmeasurable by hook name; FP rate unknown | `hook-blocks:bash_antipattern_warn above 5/session` | hypothesis |
| 2026-07-20 | gh-6: Added 4-category failure attribution (code/env/tool/unknown) to workflow-insights Step 9 friction section and summary format; retro Step 1 reads attribution weights. Transient collapsed into code (retry unknown) — parser emits no retry sequences. Spec deferred to v2. | Error counts (119 command_failed, 52 file_not_found, 28 permission_denied) had no category — retro couldn't differentiate env vs code remediation | `presence:failure-attribution-section-in-summary` | hypothesis |
| 2026-07-20 | gh-3: Design skill trio — 4 design-* skill descriptions rewritten with role anchors + trigger phrases; design-prototype gets disable-model-invocation + allowed-tools | Design skills unfindable by /slash dispatch — descriptions were capability statements, not trigger-oriented | `presence:design-skill-invocation within 10 sessions` | hypothesis |
| 2026-07-20 | gh-5: sync-global-skills.sh — DELIBERATELY_EXCLUDED[] array + reverse guard warns on unknown global skills; 6 vendored skills synced to reservoir | Template skills drifted from canonical ~/.claude/ — no mechanism detected new globals missing from vendor list | `absence:unaccounted-reservoir-skill for 3 retros` | hypothesis |
| 2026-07-20 | gh-8: ci_drift_warn.sh — PostToolUse advisory hook warns on missing working-directory paths + local uses: refs in workflow YAMLs; macOS-safe (perl -nle) | 3 CI jobs referenced deleted paths; no hook caught CI-vs-repo drift | `absence:broken-ci-path-on-main for 5 sessions` | hypothesis |
| 2026-07-20 | Parallax integration plan: canonical finding schema + evidence model in refs/, review-shared skill, skills: preloading on agents, SANYI evals, merge-verdict gate on /code-pr | akira and sanyi report in incompatible formats; no evidence classification; /code-pr is single-pass with no merge verdict; sanyi has 0 evals vs akira's 23 | `presence:review-shared-skill-invoked within 3 L2+ reviews` | hypothesis — PLANNED (5 phases) |
