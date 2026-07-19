# Handover — 2026-07-20 Cross-Repo Plan Sweep + Implementation Sprint

**Context**: Meta-session that scanned all repos for open plans, spawned 10+ agents to close them, and drove most plans to EXECUTED status.

## Current State

**All major plans now EXECUTED or research-complete:**

| Repo | Plan | Status |
|------|------|--------|
| ai-project-template | consolidate-capability-reference | EXECUTED (all 5 phases) |
| ai-project-template | genesis-lifecycle-architecture | EXECUTED (interview shrink + capabilities catalog) |
| ai-project-template | two-root-scaffold | EXECUTED (all 4 phases) |
| ai-project-template | Vercel branch + guards.ts | Done (new-agent updated, security scaffold created) |
| ai-project-template | audit_capabilities.py | Done (folded into validate_paths.py) |
| guacamayo | skills-refs-evals-norm | EXECUTED (P5b deferred) |
| playground | rag-latency E1 | Done (async streaming in answer node) |
| playground | eval dataset | Fixed (English, matches music corpus) |

**Worktree changes need merging.** Several agents ran in worktree isolation against ai-project-template. Ramsey needs to review and merge/commit the worktree branches.

**Nothing is IN PROGRESS.** All plans are either EXECUTED, SUPERSEDED, or deferred with clear blocking conditions.

## Decisions Made

- Skills-evals-norm Phase 5b (ADK eval adoption): deferred — blocked on labeling decision. Template's eval harness is the reference pattern; ADK repos follow with adjustments.
- Playground RAG: E2 (Flash 2.0) marked OBSOLETE (already on 2.5 Flash). E1 streaming implemented. Eval dataset rewritten to match actual music corpus.
- Convention refs: 9 agent-*.md files are the canonical tooling-agnostic layer. Framework refs (langgraph, google-adk, adk-vercel) narrowed to <70-line bindings pointing into them.
- English-only eval datasets. Always verify synthetic data matches the actual corpus.

## Open Threads

- ai-project-template has multiple worktree branches from parallel agents — need cherry-picking or merging into main working tree
- Playground RAG experiments E3-E6 still viable but lower priority (E1 was the big TTFT win)
- `evals/graders/*.py` scaffold files referenced in capabilities catalog don't exist as static template files (render-time outputs) — 4 info-level warnings from validator
- Ghost skills `dream`/`grow-companion` were removed from copier.yaml prune task (they were never created for the template)

## Immediate Next Steps

1. Review and merge worktree changes for ai-project-template (multiple agents wrote to isolated branches)
2. Commit all pending changes across repos (Ramsey commits)
3. Consider `/dream` to close the session properly (3 growth entries pending)
4. Next substantive work: playground RAG E3/E4 experiments, or pick up DSSG work

## Key Files

- `guacamayo/.claude/docs/plans/2026-07-18-skills-refs-evals-norm.md`
- `ai-project-template/.claude/docs/plans/2026-07-20-consolidate-capability-reference.md`
- `ai-project-template/.claude/docs/plans/2026-07-19-two-root-scaffold.md`
- `ai-project-template/.claude/docs/plans/2026-07-19-genesis-lifecycle-architecture.md`
- `playground/.claude/docs/plans/rag-latency-optimization.md`
- `playground/data/eval_data/eval_v2.jsonl`
