# Handover — 2026-07-24 Observability Loop Fix + Review Fixes

**Context**: Guacamayo meta session. Fixed review findings (F-R1/F-R2/F-R3), wired the observability loop (/grow spawns insights, /dream spawns retro), consolidated all changes onto GUA-23-review-backbone.

## Current State

All changes uncommitted on `GUA-23-review-backbone`. Ready to commit. Key changes:

**Observability loop wiring (new this grow):**
- `/grow` now background-spawns `/workflow-insights` (haiku) at Step 4a
- `/dream` now background-spawns `/workflow-retro` (sonnet) at Phase 8 if triggered
- Signal summary split: separate `Insights:` date and `Retro:` date (were conflated)
- CLAUDE.md lifecycle table updated to reflect background spawns
- Retro overdue check now reads `tooling-ledger-log.md` R# date, not insights-log

**Review fixes (from prior grow):**
- F-R1: `.claude/docs/state/` → `.sounding/state/` (git rm + add, shows as renames)
- F-R2: README.md stale tooling-ledger path → `.sounding/tooling-ledger.md`
- F-R3: wake/grow/dream "H1 date" → `## YYYY-MM-DD` section header format

**From earlier session (retro R1):**
- Tooling ledger split: active + archive
- Insights-log (append-only, replaces insights-summary)
- State files migrated to `.sounding/`
- Dream Phase 8 trigger 3 (independent tooling-change detection)
- PULL_STRATEGY variable, bash hook deleted

**Known broken:**
- `scripts/pulse.sh` — regex targets `<section id="pulse">` but dashboard now has cost/context/friction/experiments tabs
- `make pulse` fails — needs rewrite for new dashboard structure

## Decisions Made

- **Consolidate to GUA-23**: All changes (retro R1 + review fixes + loop wiring) go on one branch
- **Background agents for observability**: insights and retro run as spawned agents, not inline — protects context windows
- **Separate insights vs retro dates**: These track different things (analysis vs action) and need independent staleness checks
- **pulse.sh is broken**: Known, don't fix mid-commit — separate issue

## Open Threads

- **pulse.sh rewrite**: Needs to match new dashboard tab structure. Could fold into GUA-26.
- **6 cross-repo PRs still awaiting merge**
- **`make ship-all`**: Ramsey wants workspace-level shipping target
- **`bug/worktree-auto-cleanup` branch**: Orphaned — delete after GUA-23 commit

## Immediate Next Steps

1. **Commit on GUA-23** — all changes ready
2. **Push + update/create PR**
3. **Delete orphaned `bug/worktree-auto-cleanup` branch**
4. **Merge 6 cross-repo PRs**
5. **Fix pulse.sh** — align with new dashboard tabs (new issue or GUA-26)

## Key Files

- `.claude/skills/grow/SKILL.md` (Step 4 split into 4a spawn + 4b signals)
- `.claude/skills/dream/SKILL.md` (Phase 8 → background agent)
- `.claude/skills/wake/SKILL.md` (path + format fixes)
- `CLAUDE.md` (lifecycle table updated)
- `.sounding/tooling-ledger.md`, `.sounding/tooling-ledger-log.md`, `.sounding/insights-log.md`
- `.sounding/state/` (migrated from `.claude/docs/state/`)
- `scripts/pulse.sh` (BROKEN — needs rewrite)
