# Handover — 2026-07-22 Retro + Workflow Simplification + Dream

**Context**: Tooling retro session that expanded into workflow skill redesign. Ran /workflow-retro → applied 6 findings → researched skill landscape → executed Phase 1 of #9 (code-pr merged into workflow-review) → /grow → /dream with synthesis.

## Current State

**Retro findings applied (6 of 8):**
- F1/F2: >150k context and failure attribution hypotheses graduated (rolled into ledger rollup)
- F4: Default model changed opus→sonnet in settings.json (biggest cost lever)
- F5: Ledger compressed 51→30 lines
- F6: Parallax sanyi duplicate deleted
- F8: Worktree timing guidance added to CLAUDE.md

**Deferred:**
- F3: Bash antipattern hook removal (watching one more window)
- F7: Expanded into #9 workflow simplification

**Workflow simplification (#9) — Phase 1 EXECUTED:**
- `/code-pr` deleted — absorbed into `/workflow-review`
- `/workflow-review` rewritten: plan fidelity + multi-reporter orchestration + DoD + merge verdict
- All active config refs updated (hooks, refs, review-shared, CLAUDE.md, README.md, models.md, sanyi evals)
- Zero stale `code-pr` references in active config (historical docs preserved)
- Global skill count: 25→24

**All changes uncommitted.** Ramsey needs to commit the retro + Phase 1 batch.

**Dream synthesis ran:** 12 growth entries processed — identity seeds transformed.

## Decisions Made

- **Model default**: sonnet globally. Opus via explicit `claude --model opus` for planning/retro/dream/audit.
- **Merge direction**: /workflow-review absorbs /code-pr (pipeline name is the anchor)
- **Fable for review**: /workflow-review recommended at fable tier for diff analysis
- **Quality gates**: `make precommit → make test → make pull/rebase → /code-review → /docs-check → push` (pre-push). `/workflow-review <PR#>` (post-PR).
- **Config > instruction**: settings.json is the only enforceable lever for model defaults; CLAUDE.md text is advisory.

## Open Threads

- **sync-global-skills.sh**: May have stale `code-pr` in SKILLS[] array — check before next template sync.
- **Weekly meta automation**: Phase 2 of #9 — /dream should flag when retro >7 days overdue.
- **Skill consolidation**: Broader interest in reviewing all skills for overlap. code-pr was the clearest case.

## Immediate Next Steps

1. Ramsey commits all retro + Phase 1 changes
2. Check sync-global-skills.sh for stale code-pr reference
3. Phase 2-3 of #9 (dream retro nudge + docs update) — sonnet session
4. Resolve learn-ai-engineering rebase, commit agent work
5. `/workflow-refine` on #4 and #9 to check DoR

## Key Files

- `~/.claude/settings.json` (model: sonnet)
- `~/.claude/CLAUDE.md` (skill groups, review ladder, session hygiene updated)
- `~/.claude/skills/workflow-review/SKILL.md` (rewritten)
- `~/workspace/guacamayo/.claude/docs/tooling-ledger.md` (compressed to 30 lines)
- `~/workspace/guacamayo/.claude/docs/plans/2026-07-22-workflow-simplification.md` (Phase 1 done, 2-3 remain)
