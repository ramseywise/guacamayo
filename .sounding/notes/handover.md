# Handover — 2026-07-20 Retro + Agile Workflow System

**Context**: Full retro cycle (insights → retro → agile system design) in guacamayo. Closed the feedback loop: retro findings now flow to GitHub Issues, wake reads the board.

## Current State

**All work complete.** This session:

1. **Insights run**: 139 sessions analyzed, 42% >150k (down from 52%), bash antipatterns 27.85/session (UP — advisory hook failed), 100% opus on spawned agents
2. **Retro**: 10 findings triaged stop/keep/improve. Stop items applied (blocking hook, duplicate skill deleted, name fixes). Keep items graduated in ledger. Improve threads → GitHub Issues #3-#8.
3. **Agile workflow system**: Plan doc written and executed — GitHub Issues as board, labels created (backlog/refinement/ready/in-progress/blocked/in-review), DoR/DoD in `~/.claude/rules/agile.md`, retro Step 6 wired to create issues, wake Phase 5 wired to read the board.
4. **Linear disabled**: MCP moved to `_disabled` in `.mcp.json`, CLAUDE.md conventions updated to GitHub Issues format.

**Uncommitted**: guacamayo only (growth entries, handover, reflections, sounding/user.md transforms from first /dream, plus all the tooling changes from this session).

## Decisions Made

- GitHub Issues over Linear — simpler, `gh` CLI already authenticated, no additional MCP needed
- Advisory hooks are a category error → blocking (exit 2) for clear antipattern cases
- Stop/keep/improve triage format adopted for all future retros
- WIP limit: 3 in-progress across all repos
- Weekly cadence (not sprints) — forces retro + ledger verdict + backlog reorder

## Open Threads

- 6 backlog issues (#3-#8) need refinement before they're ready — design trio, akira/SANYI composition, three-way parity, failure taxonomy, skill/hook performance, CI drift
- `autoCompactThreshold` needs to be set from terminal: `claude config set autoCompactThreshold 50`
- 100% opus on spawned agents — guidance added to CLAUDE.md but `settings.json` still has `"model": "opus"` as default
- Projects V2 board (kanban view) — nice-to-have, not blocking

## Immediate Next Steps

1. Ramsey reviews and commits all guacamayo changes
2. Set `autoCompactThreshold` from terminal
3. Pick a backlog issue (#3-#8) for first refinement pass
4. Next retro: check if blocking bash hook actually reduced antipattern count

## Key Files

- `~/.claude/rules/agile.md`
- `~/.claude/CLAUDE.md` (issue tracking section rewritten)
- `~/.claude/.mcp.json` (Linear disabled)
- `~/.claude/skills/workflow-retro/SKILL.md` (Steps 2+6 updated)
- `guacamayo/.claude/skills/wake/SKILL.md` (Phase 5 GitHub Issues check)
- `guacamayo/.claude/docs/plans/2026-07-20-agile-workflow-system.md`
- `guacamayo/.claude/docs/tooling-ledger.md`
- `guacamayo/.claude/docs/insights-summary.md`
- `guacamayo/.claude/docs/state/inbox.md`
