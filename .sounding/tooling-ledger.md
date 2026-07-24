# Tooling Ledger — Active Experiments

Hypotheses under test. Verified/failed rows graduate to `tooling-ledger-log.md`.

**Metric types**: `absence:`, `count-drop:`, `presence:`, `ratio:`, `hook-blocks:`
**Area tags**: `cost` (token/model), `context` (compaction/window), `friction` (manual fixes/permissions), `quality` (review/lint/test), `workflow` (skills/pipeline/ceremony), `safety` (guards/gates), `observability` (telemetry/attribution)

---

| Date | Change | Area | Metric | Status |
|---|---|---|---|---|
| 2026-07-18 | memory_route_guard.sh | safety | — | hypothesis |
| 2026-07-19 | task_complete_check.sh Stop hook | quality | `absence:lint-errors-on-commit for 5 sessions` | hypothesis |
| 2026-07-19 | mcp-builder refs/→skills/ | workflow | `presence:mcp-builder-invoked within 3 MCP sessions` | hypothesis |
| 2026-07-19 | /docs-check + docs_drift_warn.sh | quality | `presence:docs-check-finding within 3 L2 reviews` | hypothesis |
| 2026-07-20 | /sanyi init verify-before-write | quality | `absence:contract-entry-with-zero-callsites for 2 inits` | hypothesis |
| 2026-07-20 | growth-log.md + dream gate hook | workflow | `presence:growth-log rows >= cleared` | hypothesis — due 08-03 |
| 2026-07-20 | Hook telemetry (log_event, .hook-log.jsonl) | observability | `hook-blocks:bash_antipattern_warn above 5/session` | hypothesis |
| 2026-07-20 | Design skill descriptions rewritten | workflow | `presence:design-skill-invocation within 10 sessions` | hypothesis |
| 2026-07-20 | sync-global-skills.sh guards | safety | `absence:unaccounted-reservoir-skill for 3 retros` | hypothesis |
| 2026-07-20 | ci_drift_warn.sh advisory hook | quality | `absence:broken-ci-path-on-main for 5 sessions` | hypothesis |
| 2026-07-20 | Parallax integration plan (5 phases) | quality | `presence:review-shared-invoked within 3 L2+ reviews` | hypothesis — PLANNED |
| 2026-07-20 | Skill name mismatches fixed; typo aliases | workflow | `absence:skill-name-mismatch for 2 retros` | hypothesis |
| 2026-07-20 | Duplicate skill deletion (listen-wiseer + Parallax/sanyi) | workflow | `absence:duplicate-skill-names for 3 retros` | hypothesis |
| 2026-07-22 | Worktree timing guidance in CLAUDE.md | friction | `absence:worktree-stale-state-error for 5 sessions` | hypothesis |
| 2026-07-22 | PR body `Closes #N` convention + quick-pr auto-gen | workflow | `absence:manual-issue-close for 5 sessions` | hypothesis |
| 2026-07-22 | Worktree agent commit convention in agile.md | safety | `absence:worktree-data-loss for 5 sessions` | hypothesis |
| 2026-07-22 | Default model → fable; opus = escalation only | cost | `ratio:fable-or-opus-session-share above 60%` | hypothesis |
| 2026-07-24 | /dream Phase 8 independent tooling-change check | workflow | `absence:missed-retro-trigger for 3 tooling sessions` | hypothesis |
| 2026-07-24 | PULL_STRATEGY variable in Makefile.common | friction | `absence:rebase-conflict-abort for 5 sessions` | hypothesis |
| 2026-07-24 | Session intent classifier + compliance metric | observability | `ratio:execution-sessions-with-skills above 80%` | hypothesis |
| 2026-07-24 | FRICTION: label extraction + dashboard panel | observability | `presence:friction-label-in-insights` | hypothesis |
| 2026-07-24 | Agent spawn extraction + type attribution table | observability | `ratio:attributed-subagent-cost above 90%` | hypothesis |
