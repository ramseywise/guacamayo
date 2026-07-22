# Handover — 2026-07-22 Pipeline Reorder + Make Lint

**Context**: Continuing the workflow infrastructure session. Reordered the process pipeline, renamed precommit→lint, updated all config files.

## Current State
- Workspace Makefile: `lint` is the primary target, `precommit` is an alias. Help text shows the full pipeline.
- Global CLAUDE.md: pipeline updated to groom → research → plan → refine → execute → review → ship
- agile.md: ceremony table expanded to 8 rows (groom, research, plan, refine, execute, review, ship, retro)
- Guacamayo CLAUDE.md: process layer pipeline updated
- All "make precommit" references → "make lint" across quality gates and DoD
- **Uncommitted**: workspace Makefile, global CLAUDE.md, agile.md, guacamayo CLAUDE.md, growth.md, this handover

## Decisions Made
- **Pipeline order**: groom → research → plan → refine → execute → review → ship. Refine is a DoR gate AFTER plan, not backlog triage before research.
- **`lint` over `precommit`**: clearer naming. `precommit` kept as alias for backward compat.
- **Akira-wander = grooming tool**: finds backlog items at the front of the pipeline.
- **Review ladder stays as-is**: scan inside L2+, wander separate (exploratory), sanyi inside L3.

## Open Threads
- **Dependabot auto-resolve**: needs a skill or `make deps` target — backlog idea
- **`make groom`**: would print `/akira wander` command — easy add when ready
- **GUA #11**: lifecycle ceremony redesign (backlog)
- **GUA #12**: fable model integration (backlog)
- **JOB PRs**: JOB-bootstrap branch needs PR creation + issue closure (#1-5)
- **LAE PRs**: LAE-39-structural-cleanup branch needs PR creation + issue closure (14 issues)

## Immediate Next Steps
1. Commit all changes across repos (Ramsey commits)
2. Run `make status` from workspace to see full picture
3. Run `make ship` to push and create PRs for any open branches
4. Consider creating GUA issue for dependabot auto-resolve skill

## Key Files
- `~/workspace/Makefile`
- `~/.claude/CLAUDE.md`
- `~/.claude/rules/agile.md`
- `~/workspace/guacamayo/CLAUDE.md`
- `~/workspace/guacamayo/.sounding/growth.md`
