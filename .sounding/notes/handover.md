# Handover — 2026-07-27 Fleet Dispatch: JOB + GUA Issues + SDK Adoption

**Context**: Meta-session dispatching 14 agents across 7 repos to clear JOB and GUA open issues, execute SDK adoption strategy, and retire unused design skills.

## Current State

**Completed (staged/committed, awaiting Ramsey's review + push):**

| Work | Repo | State | Notes |
|------|------|-------|-------|
| #38 dao foundation | guacamayo | Committed (179ae17) | 101 tests, three-role dirs |
| #39 scan dimensions | guacamayo | Staged | 167 tests, 5 dimension agents + wander |
| #33 hook telemetry | ~/.claude | Unstaged | 2 bugs fixed in review-verdict-gate.sh |
| #35 branch protection | API only | Applied | 4 repos protected (librarian, atlas, listen-wiseer, AIT) |
| #37 akira simplification | ~/.claude | Committed (CLA-34 branch) | Already done prior session |
| #31 dependabot fleet | 4 repos | Staged | guacamayo, LAE, JOB, lebanese-blonde |
| #32 design retirement | ~/.claude | Staged | 4 skills → archive/ |
| #41 parser taxonomy | librarian | Committed by agent | Unknown 24%→0.5% |
| #24 gitignore | job-system | Committed (JOB-24 branch) | |
| SDK listen-wiseer | listen-wiseer | Staged | anthropic >=0.25→~=0.120 |
| SDK atlas | atlas/web | Staged | Vercel AI SDK installed |
| #28 plugins | guacamayo | Closed wontfix | |

**Lint fixed**: 3 rounds on #39 output (import sorting, unused imports, subprocess check=False). All clean now.

## Decisions Made

- **Design skills retired**: 4 skills (design-initiative, design-milestones, design-prototype, design-sprint) archived after 222 sessions / 0 invocations. Workflow structurally absorbs their function into /workflow-plan. Skill count: 24→20.
- **#28 closed wontfix**: Claude Code plugins — speculative, no mature offerings.
- **Backlog triage**: #34 umbrella (close when children ship), #36 (after #39), #40 (gated on 3+ sweeps), #30 (separate initiative). All correctly parked.
- **Retro findings approved (F1-F3, F6)**: Remove bash_antipattern hook, investigate fable vs opus default, lib.sh log_pass(), plan-doc Status enforcement. All due 08-10.
- **Branch protection**: enforce_admins=false, strict=true (requires rebase before merge). Ramsey to confirm or adjust.

## Open Threads

- **#39 orchestrator integration gap**: akira SKILL.md needs to dispatch 5 dimension agents through dao pipe. Spawn prompt in #39 agent output.
- **Worktree + denied commit = lost work**: First #38 worktree agent's work was lost because settings deny `git commit` but worktree cleanup destroys staged changes. Need either a worktree exception in settings or stop using worktree isolation. Growth entry captured.
- **Agents don't pre-lint**: Every Python agent needed post-hoc lint fixes. Consider adding "run ruff check --fix && ruff format before staging" to agent prompts or a post-agent hook.
- **JOB #31 staging conflict**: dependabot changes staged on JOB-24-gitignore-applications branch — needs separate branch or fold-in.
- **Atlas Tremor/React 19 peer dep conflict**: pre-existing, requires --legacy-peer-deps. Not introduced by SDK work.
- **Librarian #41 needs cartographer re-parse**: `cartographer --facts` to backfill corrected classifications.
- **sdk-adoption-strategy plan**: Executed (LIS + ATL done), LAE examples not yet updated. No issue needed per Ramsey.

## Immediate Next Steps

1. Review staged diffs across repos — biggest: guacamayo (review system), ~/.claude (retirement + hook fix)
2. Commit + push per repo, close issues: #24, #31, #32, #33, #35, #37, #38, #41
3. Merge JOB PR #23 → close #15, #16, #17, #18
4. Spawn #39 orchestrator integration (akira dispatch through dao pipe)
5. Update CLAUDE.md skill counts (24→20) when committing design retirement

## Key Files

- `.claude/docs/plans/2026-07-27-review-agent-architecture.md`
- `.claude/docs/plans/2026-07-27-sdk-adoption-strategy.md`
- `review/dao/signals.py`, `review/scan/agents/*.md`, `review/wander/agents/wander.md`
- `~/.claude/archive/design-skills-retired/README.md`
- `~/.claude/hooks/review-verdict-gate.sh`
- `.sounding/growth.md` (4 entries)
