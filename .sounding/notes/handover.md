# Handover — 2026-07-26 Cross-Repo Pipeline Dispatch

**Context**: Meta-session dispatching agents across job-system and learn-ai-engineering to move 15+ backlog issues through plan→refine→execute. Also fixed /wake and /grow to check all repos.

## Current State

**job-system**: #10-14 closed. #15-18 DONE (committed on `JOB-15-pipeline-work` branch). #19 PARTIAL — browser-capture URLs need chrome MCP session + Ramsey input. Plan: `job-system/.claude/docs/plans/2026-07-25-JOB-15-19-pipeline-work.md` (Status: IN PROGRESS).

**learn-ai-engineering**: #30 executed (committed on `LAE-30-rl-depth-content`). #35, #37 executed (committed on `LAE-35-staleness-migrations`). #36 Phase 2 (tf.contrib→tf.keras rewrite) NOT YET DONE — needs separate session. #34 agent was spawned (learning skill + librarian arxiv fetch + cron) — check completion. Plan: `learn-ai-engineering/.claude/docs/plans/2026-07-25-LAE-30-34-learning-depth.md` (Status: PLANNED — not updated by agents).

**guacamayo**: Uncommitted changes on main — wake/grow skill fixes (cross-repo gh loop), growth.md updates, handover. Need `bug/` branch + commit.

**Branches needing PRs**: `JOB-15-pipeline-work`, `LAE-30-rl-depth-content`, `LAE-35-staleness-migrations`.

## Decisions Made

- **/workflow-refine must use fable, not sonnet** — sonnet defers verification questions instead of resolving them. Process learning for /retro.
- **Serialize worktree agents per-repo** — two agents in same repo caused branch collision (LAE #30 commits on #35 branch). Fixed by branch rename + fresh branch from main.
- **Agent rebase convention** updated: `git fetch origin main && git rebase origin/main` (not `git pull --rebase`).

## Open Threads

- **LAE #34 agent** may still be running — check task status. Covers librarian arxiv fetch + LAE learning skill.
- **LAE #36 Phase 2** (tf.contrib→tf.keras for Ng DL notebooks) — separate execute session needed.
- **LAE-35-staleness-migrations push rejection** — remote had old #30 commits. Needs `--force-with-lease` or delete+re-push.
- **22 hypothesis rows** in tooling ledger — 13 from July 18-20 approaching 2-week stale threshold.
- **pulse.sh broken** — regex targets old dashboard structure (carried from prior session, still unfixed).
- **companion-summarizer plan** still IN PROGRESS with uncommitted work (paused July 20).
- **GUA-28** (CLA: Claude Code plugins) — new backlog issue on guacamayo board.

## Immediate Next Steps

1. Check LAE #34 agent completion — verify librarian + LAE learning skill work
2. Ramsey: push branches + create PRs for `JOB-15-pipeline-work`, `LAE-30-rl-depth-content`, `LAE-35-staleness-migrations`
3. Create `bug/` branch on guacamayo, commit wake/grow skill fixes
4. Spawn LAE #36 Phase 2 execute session (tf.contrib→tf.keras)
5. Close issues after PR merge: job #15-19, LAE #30, #35, #37 (hold #36 for Phase 2)

## Key Files

- `.claude/skills/wake/SKILL.md:83` (cross-repo gh loop)
- `.claude/skills/grow/SKILL.md:62` (cross-repo gh loop)
- `.sounding/growth.md` (5 entries — synthesis due at /dream)
- `job-system/.claude/docs/plans/2026-07-25-JOB-15-19-pipeline-work.md`
- `learn-ai-engineering/.claude/docs/plans/2026-07-25-LAE-30-34-learning-depth.md`
