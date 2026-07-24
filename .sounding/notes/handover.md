# Handover — 2026-07-24 Cross-Repo Shipping Complete

**Context**: Meta session in guacamayo. Shipped review backbone (GUA-23) work across 6 repos — review artifacts, worktree cleanup, branch hygiene, make ship pipeline.

## Current State

All 6 PRs are pushed and reviewed. Ramsey has not yet merged:

| Repo | PR | Branch | Verdict |
|------|----|--------|---------|
| guacamayo | #25 | `GUA-23-review-backbone` | approve |
| dotclaude (~/.claude) | #1 | `GUA-16-review-artifact-contract` | approve |
| learn-ai-engineering | #74 | `LAE-39-structural-cleanup` | approve |
| ai-project-template | #18 | `AIT-makefile-updates` | approve |
| atlas | #26 | `ATL-22-remove-pycache` | approve |
| librarian | #41 | `LIB-makefile-dependabot` | approve |

Growth: 5 entries — synthesis due at next /dream.

## Decisions Made

- **Review scope detection**: lightweight (chore/bug/style, no plan doc) vs full (feature + plan doc). Auto-detected from branch prefix + commit types + plan doc presence. Implemented in workflow-review Stage 0.
- **Stage 0.5 worktree check**: `git worktree list` + stale branches + unmerged agent branches — added to workflow-review before code review starts.
- **`make review` is a print target**: prints `/workflow-review` reminder, not an automated runner. Review is judgment, not lint.
- **LAE rebase strategy**: dependabot-heavy branches use `git merge main`, not rebase. The new `make pull` (rebase-based) doesn't work for these — may need per-repo override.
- **Atlas pre-existing lint**: 22 ruff errors are pre-existing, not from ATL-22. Pushed anyway; separate cleanup PR needed.
- **Force-with-lease for own branches**: safe after rebase rewrites history on already-pushed branch.

## Open Threads

- **`make ship-all` at workspace level**: Ramsey explicitly wants this. Not yet built. Would iterate repos and run `make ship` per repo, collecting results.
- **LAE `make pull` incompatibility**: The rebase-based pull in Makefile.common fails on dependabot-heavy branches. Needs either a per-repo `PULL_STRATEGY=merge` override or smarter conflict detection.
- **Atlas lint cleanup**: 22 ruff errors (import sorting, unused vars) need a dedicated PR.
- **Post-merge branch cleanup**: After PRs merge, delete feature branches (GUA-16, GUA-17, GUA-18 on guacamayo; stale branches on other repos already cleaned).
- **Worktree auto-cleanup**: Agent worktrees persist after completion, causing pre-commit SKIP noise. Could be solved by a post-agent hook or make target.

## Immediate Next Steps

1. **Merge 6 PRs** — all approved, Ramsey's call on order
2. **Delete feature branches** post-merge (GUA-16, GUA-17, GUA-18 on guacamayo)
3. **Atlas lint PR** — fix 22 pre-existing ruff errors in a separate branch
4. **`make ship-all`** — design and implement workspace-level shipping (new issue)
5. **`/dream`** — 5 growth entries, synthesis due

## Key Files

- `~/.claude/Makefile.common` (updated pull + review targets)
- `~/.claude/skills/workflow-review/SKILL.md` (Stage 0 + 0.5)
- `~/workspace/guacamayo/.claude/docs/plans/2026-07-24-GUA-23-review-verdict.md`
- `~/workspace/guacamayo/.sounding/growth.md` (5 entries)
- `~/workspace/learn-ai-engineering/.pre-commit-config.yaml` (new)
