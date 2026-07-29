# Tooling Ledger — Archive

Graduated experiments. Append-only. Active hypotheses live in `tooling-ledger.md`.

**Area tags**: `cost` (token/model), `context` (compaction/window), `friction` (manual fixes/permissions), `quality` (review/lint/test), `workflow` (skills/pipeline/ceremony), `safety` (guards/gates), `observability` (telemetry/attribution)

---

## R0 — 2026-07-22 (pre-numbered retros, batch graduation)

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07 (rollup) | 20 verified/failed: Bash patterns, /retro+ledger, cartographer, v2→v3, doc-artifact, akira, commands/, wake-nudge, model pairing, git-ignore .claude/docs/, shell.md safety, /grow, experiment tracking | mixed | verified/failed | >150k context 66%→37% confirmed; bash_antipattern blocking 26.4 flat failed |
| 2026-07-17 (batch) | 11/12 infra: sanyi, sync-global, zsh, skill dedupe, librarian ingest, phase-protocol, rules→refs, review-sweep, review ladder, compact-wiki, repo-security | mixed | verified | All actively working. retrieval telemetry split out (inconclusive) |

## R1 — 2026-07-24

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-18 | memory_route_guard.sh | safety | verified | Hook exists, 0 misroutes across 6+ sessions |
| 2026-07-20 | Plan-doc ABANDONED status | workflow | verified | Used in 2 plans: agile-workflow-system, listen-wiseer phase7a |
| 2026-07-20 | Bash antipattern advisory→blocking | friction | failed | 26.4/session flat for 3 windows. Hook removed |
| 2026-07-20 | Spawn model guidance + default→sonnet | cost | superseded | Replaced by fable default (2026-07-22). 60% opus pre-change |
| 2026-07-22 | Ledger compressed 51→30 lines | workflow | verified | Split to active+archive format |
| 2026-07-22 | `make status/push/quick-pr` targets | workflow | verified | Used across 6 repos via make ship |

### R1 findings applied
- F1: Ledger split into active + archive (this file)
- F2: `bash_antipattern_warn.sh` deleted (failed experiment)
- F4: /dream Phase 8 independent tooling-change detection added
- F5: `PULL_STRATEGY` variable added to Makefile.common
- F6: Worktree auto-cleanup → backlog issue #27

## R5 — 2026-07-29

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-29 | Review-findings persistence: required-field list inlined in workflow-review Stage 4b + finding-schema example | observability | verified | 7 rows in review-findings.jsonl, all 7 pass full-schema validation (id, source, date, repo, file, title, merge_impact, evidence_state present); day-1 conformance met |
| 2026-07-28 | Insights placement settled: engine+data in librarian, rendered artifacts in guacamayo/.sounding | observability | verified | 2 retros (R4+R5): context-dashboard.html, insights-log.md, insights-report.html confirmed in .sounding/; no artifacts found outside .sounding/; state doc authoritative |

### R5 findings applied
- F1: Review-findings persistence graduated verified — 7/7 rows schema-conformant on day 1
- F2: Insights artifact placement graduated verified — 2 retro windows clean
- F3: Plan-doc Status enforcement still failing — `2026-07-24-GUA-23-review-verdict.md` has no Status line; `2026-07-22-workflow-simplification.md` uses `**Status**:` (bold) not bare `Status:` prefix — both need fixup
- F4: p90 output tokens unchanged at 956/msg (latest insights: 22% >150k, no trend improvement) — verbosity cap hypothesis active, due 08-24
- F5: TodoWrite enforcement: 69+ long sessions still run without TodoWrite across R4+R5 window — hook not yet wired, hypothesis active
- F6: Bash error stratification still in cartographer backlog — no signal in R5 insights; hypothesis active, due 08-17

### R5 config proposals (pending Ramsey approval — do not auto-apply)

**P1: Fix Status line format in 2 stale plan docs** — `2026-07-24-GUA-23-review-verdict.md` needs `Status: COMPLETE` (merge verdict = approve; merged). `2026-07-22-workflow-simplification.md` already has `**Status**: EXECUTED` but grep for `^Status:` misses it — either normalize to bare `Status:` prefix or update the enforcement check to match bold variant.

**P2: Wire TodoWrite hook** — PostToolUse/Bash: if cumulative bash_calls > 100 and no TodoWrite in session, emit structured warning. Pattern persists across R4+R5 (69+ sessions blind). Metric: `ratio:TodoWrite-in-heavy-sessions above 50% by 2026-08-09`. See R4 P1 for draft mechanism.

**P3: Add ≤400-token output budget to wake/grow/dream prompts** — p90 at 956 tokens/msg unchanged across 2 retros. Quick change: add one instruction line to each identity skill prompt. Metric: `p90:output-tokens-per-msg below 700 by 2026-08-24`.

**P4: Retire or redesign design-* skills** — 0 invocations across 3 retro windows (227+ sessions). Options: (a) add invoke examples to CLAUDE.md, (b) consolidate to `/design` dispatch, (c) close backlog and remove. Decision needed before R6.

## R4 — 2026-07-28

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-24 | PULL_STRATEGY variable in Makefile.common | friction | verified | 0 rebase-conflict-abort events across 227 sessions (5-session threshold met) |
| 2026-07-27 | Remove bash_antipattern_warn.sh from settings+disk (F1) | friction | verified | Hook absent from disk and settings.json at R4 check; R3 approved action confirmed applied |
| 2026-07-27 | Investigate/change model default fable vs opus (F2) | cost | verified | settings.json model = `claude-fable-5[1m]`; fable is default, opus = escalation only; 87%+ opus cost-weighted is justified escalation pattern not default mismatch |
| 2026-07-24 | FRICTION: label extraction + dashboard panel | observability | failed | Not present in insights-log 2026-07-27 or 2026-07-29 (2 consecutive runs). Cartographer parser gap, not a config lever |
| 2026-07-24 | Agent spawn extraction + type attribution table | observability | failed | No signal in insights-log 2026-07-27 or 2026-07-29 (2 consecutive runs). Subagent cost attribution requires parser work (cartographer) |
| 2026-07-26 | Design skill description optimization (via skill-creator) | workflow | failed | 0 invocations across 227 sessions; 2 retro windows. Descriptions not the blocker — skills are workflow-fit gap. Retire or redesign |

### R4 findings applied
- F1: PULL_STRATEGY graduated verified
- F2: bash_antipattern_warn.sh removal graduated verified
- F3: Model default fable graduated verified
- F4: FRICTION label + agent attribution graduated failed → cartographer parser backlog
- F5: Design skill optimization graduated failed → skill-creator retirement audit backlog
- F6: 4 new hypotheses added (TodoWrite hook, bash stratification, verbosity cap, session breakpoints)
- F7: Plan-doc Status enforcement remains active (failing — 2 docs missing Status)

### R4 config proposals (pending Ramsey approval — do not auto-apply)

**P1: Add TodoWrite enforcement hook** — PostToolUse/Bash: if cumulative bash_calls > 100 and no TodoWrite logged, emit structured warning. Target: reduce context drift in 30% of heavy sessions.

**P2: Retire design-* skills or rewrite as invoke-on-demand** — `/design-sprint`, `/design-initiative`, `/design-milestones`, `/design-prototype` show zero invocations across 2 retro windows (227 sessions). Options: (a) add to `make help` output + CLAUDE.md examples, (b) consolidate into `/design` dispatch, (c) close backlog issues and remove.

**P3: Add ≤400-token output budget line to identity skills** — wake/grow/dream prompts. p90 output tokens 956/msg; 5× cost multiplier at that range. Mechanism: add `Keep output under 400 tokens` to each skill's instruction block.

**P4: Add Status: line to 2 stale plan docs** — `/Users/wiseer/workspace/guacamayo/.claude/docs/plans/2026-07-22-workflow-simplification.md` and `2026-07-24-GUA-23-review-verdict.md` missing `Status:` header. Quick fix: prepend `Status: ABANDONED` or `Status: COMPLETE` to each.

## R3 — 2026-07-27

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-20 | sync-global-skills.sh guards | safety | verified | 3/3 retros: 0 unaccounted reservoir skills — threshold met |
| 2026-07-20 | Duplicate skill deletion (listen-wiseer + Parallax/sanyi) | workflow | verified | 3/3 retros: 0 duplicate skill names in active repos |
| 2026-07-22 | Worktree timing guidance in CLAUDE.md | friction | verified | 0 stale-state errors across 222 sessions (5-session threshold met) |
| 2026-07-22 | Worktree agent commit convention in agile.md | safety | verified | 0 data-loss events across 222 sessions (5-session threshold met) |
| 2026-07-19 | task_complete_check.sh Stop hook | quality | inconclusive | R3 deadline: no lint errors on commit triggered in any window |
| 2026-07-19 | mcp-builder refs/→skills/ | workflow | inconclusive | R3 deadline: no MCP sessions in 3 retro windows |
| 2026-07-19 | /docs-check + docs_drift_warn.sh | quality | inconclusive | R3 deadline: no L2 reviews triggered in window |
| 2026-07-20 | /sanyi init verify-before-write | quality | inconclusive | R3 deadline: no SANYI inits in 3 retro windows |
| 2026-07-20 | ci_drift_warn.sh advisory hook | quality | inconclusive | R3 deadline: no broken CI paths in 3 retro windows |
| 2026-07-22 | PR body `Closes #N` convention + quick-pr auto-gen | workflow | inconclusive | R3 deadline: mixed evidence, no clean signal |
| 2026-07-26 | Hook telemetry wiring audit (hooks call log_event) | observability | failed | Hook log: 1 entry (test_hook only). All hooks DO call log_event — wiring correct. Issue is trigger rate: conditions rarely met. Threshold `count-drop:unique-hooks-in-log above 5` not met at R3 |

### R3 findings proposed (pending Ramsey approval)
- F1: Remove bash_antipattern_warn.sh from settings.json + delete hook file (config-ledger divergence: recorded as removed in R1 but still wired)
- F2: Investigate model default field (settings.json model: opus-4-6, not fable — fable-default experiment may not have landed)
- F3: Add log_pass() to lib.sh for exit-0 hook fire-rate visibility
- F4: Graduate 6 untestable + 4 verified rows (this section)
- F5: Plan-doc Status line enforcement for 2 docs missing Status
- F6: Create GitHub issue for unknown-error taxonomy gap (35.3%, 3 retros flat)

## R2 — 2026-07-26

| Date | Change | Area | Verdict | Evidence |
|---|---|---|---|---|
| 2026-07-18 | memory_route_guard.sh | safety | duplicate | Already graduated in R1; row left in active ledger by mistake |
| 2026-07-22 | Default model → fable; opus = escalation only | cost | verified | 88%+ fable+opus share (target ≥60%) — insights-log 2026-07-27 |
| 2026-07-20 | Design skill descriptions rewritten | workflow | failed | 0 invocations across 219 sessions; insights-log R4 flags zero-invoked design skills |
| 2026-07-20 | Hook telemetry (log_event, .hook-log.jsonl) | observability | failed | 89 log entries, only test_hook fires; hooks don't call log_event consistently |
| 2026-07-20 | Skill name mismatches fixed; typo aliases | workflow | verified | 0 mismatches across 2 retros (threshold: 2) |
| 2026-07-20 | Parallax integration plan (5 phases) | quality | inconclusive | Plan executed but review-shared never invoked — no L2+ reviews occurred to test |

### R2 findings applied
- F1: Duplicate memory_route_guard.sh row removed from active ledger
- F2: Fable model default graduated as verified
- F3: Design skill descriptions graduated as failed → backlog issue for skill-creator optimization
- F4: Hook telemetry graduated as failed → new hypothesis for wiring audit
- F5: Skill name mismatches graduated as verified
- F6: Parallax review-shared graduated as inconclusive
- F7: 6 untestable rows annotated with R3 graduation deadline
- 2 new hypothesis rows added (design skill optimization, hook telemetry wiring)
