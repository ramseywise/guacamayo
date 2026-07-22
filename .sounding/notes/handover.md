# Handover — 2026-07-22 Retro + Workflow Rules + Dream

**Context**: Retro session expanded into workflow redesign. Then Ramsey codified strict workflow gates: issue-linked branches, conventional commits, no main commits, Parallax read-only. Dream synthesis ran (12 entries cleared). Ready to spawn agents.

## Current State

**Retro + Phase 1 of #9 applied (all uncommitted):**
- 6 retro findings applied, code-pr merged into workflow-review, 15+ refs updated
- Default model opus→sonnet in settings.json
- Ledger compressed 51→30 lines

**Workflow rules codified (also uncommitted):**
- `~/.claude/rules/agile.md` rewritten: strict gates, branch types ({PREFIX}-{NUM}-{slug}, bug/, spike/), prefix table (10 repos), conventional commits
- `~/.claude/CLAUDE.md` conventions table updated
- `~/.claude/hooks/branch_guard.sh` rewritten: blocks main commits, enforces branch naming
- `~/.claude/README.md` hook description updated

**Dream synthesis ran:** 12 growth entries → 3 woven into sounding.md, 9 discarded. Accumulator cleared.

**All changes uncommitted.** Ramsey needs to commit this batch before spawning agents.

## Decisions Made

- **No code changes without GitHub issue** (except bug/ and spike/ branches)
- **Branch naming**: `{PREFIX}-{NUM}-{slug}` for planned work, `bug/` for fixes, `spike/` for exploration
- **Prefix table**: GUA, LAE, LIS, ATL, PLG, AIT, LIB, LEB, JOB, DSG
- **Conventional commits**: `{type}({scope}): {desc} (#{num})`
- **Parallax read-only**: no changes to that repo
- **Claude never pushes**: stage + commit on branch; Ramsey reviews and pushes

## Open Threads

- **sync-global-skills.sh**: May have stale `code-pr` in SKILLS[] array
- **Weekly meta automation**: Phase 2 of #9 — /dream retro nudge
- **job-system scaffolding**: #10 created (backlog) — needs git init + GitHub remote

## Immediate Next Steps

1. Ramsey commits all changes (retro + rules + dream) and pushes guacamayo
2. Spawn 3 agents: guacamayo #9 Phase 2-3, learn-ai-engineering ready items, job-system scoping
3. Check sync-global-skills.sh for stale code-pr reference
4. Resolve learn-ai-engineering rebase

## Key Files

- `~/.claude/rules/agile.md` (rewritten — strict gates, prefix table, conventional commits)
- `~/.claude/hooks/branch_guard.sh` (rewritten — enforces branch naming)
- `~/.claude/CLAUDE.md` (conventions table updated)
- `~/.claude/skills/workflow-review/SKILL.md` (rewritten from retro)
- `~/workspace/guacamayo/.claude/docs/tooling-ledger.md` (compressed)
- `.sounding/sounding.md` (transformed — 4 entries woven)
