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
