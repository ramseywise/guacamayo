# Handover — 2026-07-24 Review Backbone Shipping

**Context**: Major shipping session — executed 7 guacamayo issues (#4, #12, #15, #16, #17, #18, #19), built review backbone with 79 tests, created two-repo shipping workflow.

## Current State

### Guacamayo (`GUA-23-review-backbone` branch)
- 5 commits on branch: backbone + lint + pycache + sanyi mapping + severity schema test
- Review artifact written: `.claude/docs/plans/2026-07-24-GUA-23-review-verdict.md` (approve)
- `make ship` should pass: lint clean, 79 tests pass, check-review has artifact
- No PR exists yet — `quick-pr` step in `make ship` will create it
- Staged: `.gitignore`, several `.sounding/` files, `Makefile`, deleted `__pycache__` files

### ~/.claude/ (`GUA-16-review-artifact-contract` branch)
- 3 prior commits + 1 staged new `Makefile`
- Ramsey needs to commit the Makefile, then `make ship`
- Changes: review artifact contract (#16), make ship wire (#17), fable model ref (#12), review-shared consolidation (#19), finding-schema ref update (#18)

### Issues closed this session
#4 (research closes it), #12 (fable model), #15 (review gate hook), #16 (review artifact contract), #17 (make ship wire), #18 (finding schema), #19 (merge/dedup consolidation)

### Remaining open
- #20 — stage transitions (backlog, needs plan)
- #21 — dashboard consolidation (backlog, linked to context-eng-v2)
- #23 — review backbone (the branch — close after PR merge)
- #24 — friction signal detection (backlog, needs research)

## Decisions Made
- Review backbone: deterministic Python (schemas, dedup, sanyi) + LLM judgment — clean separation
- `~/.claude/` gets its own lightweight Makefile (push + quick-pr, no lint/test)
- Two repos need separate PRs — guacamayo ships code, ~/.claude/ ships config
- Worktree cleanup is manual for now — leftover dirs cause pre-commit SKIP noise

## Open Threads
- **Wake board scope**: Ramsey wants ALL repos in the fleet table, not just active ones — update /wake skill
- **Worktree auto-cleanup**: agent worktrees left behind cause noise — potential GUA-25
- **CV publications**: user asked about full titles vs one-liner in tailored CVs — unanswered
- **Makefile.common PR strategy**: 5 repos still have uncommitted include lines (from prior session)

## Immediate Next Steps
1. Ramsey commits + `make ship` on guacamayo (GUA-23-review-backbone)
2. Ramsey commits Makefile + `make ship` on ~/.claude/ (GUA-16-review-artifact-contract)
3. Close #23 after PR merge
4. Address remaining backlog: #20, #21, #24

## Key Files
- `review/` — Python backbone package (schemas, validation, dedup, sanyi, commit_verification)
- `tests/review/` — 79 tests
- `.claude/docs/plans/2026-07-24-GUA-23-review-verdict.md` — review artifact
- `~/.claude/Makefile` — new lightweight ship target
- `~/.claude/Makefile.common` — shared include (from prior session)
