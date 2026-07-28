# Handover — 2026-07-28 Full Board Clearance: Refine + Execute Wave

**Context**: Meta-session clearing the entire GUA backlog through the workflow pipeline (refine → execute). Also consolidated branches across 4 repos and created the auto-label hook (#42).

## Current State

**Executed + in-review (11 GUA issues):**

| # | Title | Repo | State |
|---|-------|------|-------|
| 30 | Context Eng v2 — findings pipeline + eval | guacamayo + librarian | Worktree commit; librarian dashboard.py modified |
| 31 | Dependabot — deps-triage.sh + make deps | ~/.claude | Committed on CLA-34-review-evolution (ae8331c) |
| 32 | Design skills A+B+fix — consolidation + pipeline footers | ~/.claude | Staged on CLA-34-review-evolution |
| 33 | Hook telemetry | ~/.claude | Staged on CLA-34-review-evolution |
| 35 | Branch protection | API-only | Applied, no code |
| 36 | Reliability + ops checklist items | guacamayo | Staged on GUA-34 |
| 37 | Akira simplification | ~/.claude | Staged on CLA-34-review-evolution |
| 38 | Dao foundation | guacamayo | Committed (179ae17) on GUA-34 |
| 39 | Scan dimension agents | guacamayo | Staged on GUA-34 |
| 40 | Cross-repo intelligence Phase 3a | guacamayo | Staged on GUA-34 (fingerprint + trends + 57 tests) |
| 42 | Auto-label hook | ~/.claude | Worktree commit on CLA-34 |

**Other repos:**

| Repo | Branch | What | State |
|------|--------|------|-------|
| job-system | JOB-24-gitignore-applications | #24 gitignore + #31 dependabot | Staged |
| librarian | LIB-41-parser-taxonomy | #41 parser taxonomy | Staged |
| learn-ai-engineering | LAE-bug-dependabot-config | Dependabot config fix | Committed, needs push |

**Ready (1):** #34 (umbrella — closes when children ship)
**Backlog (4 new):** #43-46 created by #30 agent (context eng v2 follow-ups)

## Decisions Made

- **Design skills: A+B+name-fix** — consolidate milestones→initiative, wire pipeline footers, fix name bug. 24→23 skills.
- **#36 re-scoped** — overlap audit showed safety.md already covers security. Real gap: reliability + operations checklist items only.
- **#42 auto-label hook created** — workflow skills drive issue state transitions via PostToolUse on Skill tool.
- **dashboard.html deleted** — stale duplicate. Only context-dashboard.html is canonical.
- **Design skill retirement reverted** — placement question, not removal.
- **Issue workflow enforcement** — labels must track state transitions. #42 automates this.

## Open Threads

- **Agents still don't pre-lint** — 3rd session with post-hoc lint fixes. No hook/prompt fix yet.
- **~/.claude branch consolidation** — multiple agents landed on CLA-34-review-evolution. May need cherry-picking or accept as one mega-PR.
- **#30 agent created 4 new issues (#43-46)** — review: legitimate follow-ups or scope creep?
- **$CLAUDE_TOOL_INPUT shape unverified** — #42 hook tries `.name // .skill_name // .skill`. First live invocation will confirm.
- **dashboard.py over threshold** — librarian at 1441 lines (1400 limit). Needs extraction.
- **#40 Phase 3b gated** — needs 3+ real sweeps.

## Immediate Next Steps

1. Commit across repos — GUA-34, CLA-34, JOB-24, LIB-41
2. Push LAE branch: `git push -u origin LAE-bug-dependabot-config`
3. Run `/workflow-review` on GUA-34 diff to main
4. Review #43-46 (new backlog) — keep or close
5. Close #34 umbrella when children (#35-40) all merge

## Key Files

- `review/dao/fingerprint.py`, `review/dao/trends.py` (#40)
- `review/scan/dimensions/safety/SKILL.md`, `review/scan/dimensions/structure/SKILL.md` (#36)
- `~/.claude/hooks/issue_label_sync.sh` (#42)
- `~/.claude/skills/design-initiative/SKILL.md` (#32)
- `~/.claude/scripts/deps-triage.sh` (#31)
- `.claude/docs/plans/2026-07-28-GUA-42-auto-label-hook.md`
