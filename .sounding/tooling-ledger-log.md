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
