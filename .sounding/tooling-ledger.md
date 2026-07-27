# Tooling Ledger — Active Experiments

Hypotheses under test. Verified/failed rows graduate to `tooling-ledger-log.md`.

**Metric types**: `absence:`, `count-drop:`, `presence:`, `ratio:`, `hook-blocks:`
**Area tags**: `cost` (token/model), `context` (compaction/window), `friction` (manual fixes/permissions), `quality` (review/lint/test), `workflow` (skills/pipeline/ceremony), `safety` (guards/gates), `observability` (telemetry/attribution)

---

| Date | Change | Area | Metric | Status |
|---|---|---|---|---|
| 2026-07-19 | task_complete_check.sh Stop hook | quality | `absence:lint-errors-on-commit for 5 sessions` | hypothesis — untestable (no triggering condition yet; graduate R3 if still no signal) |
| 2026-07-19 | mcp-builder refs/→skills/ | workflow | `presence:mcp-builder-invoked within 3 MCP sessions` | hypothesis — untestable (no MCP sessions; graduate R3 if still no signal) |
| 2026-07-19 | /docs-check + docs_drift_warn.sh | quality | `presence:docs-check-finding within 3 L2 reviews` | hypothesis — untestable (no L2 reviews; graduate R3 if still no signal) |
| 2026-07-20 | /sanyi init verify-before-write | quality | `absence:contract-entry-with-zero-callsites for 2 inits` | hypothesis — untestable (no SANYI inits; graduate R3 if still no signal) |
| 2026-07-20 | growth-log.md + dream gate hook | workflow | `presence:growth-log rows >= cleared` | hypothesis — due 08-03 |
| 2026-07-20 | sync-global-skills.sh guards | safety | `absence:unaccounted-reservoir-skill for 3 retros` | hypothesis — trending verified (2/3 retros) |
| 2026-07-20 | ci_drift_warn.sh advisory hook | quality | `absence:broken-ci-path-on-main for 5 sessions` | hypothesis — untestable (no broken CI; graduate R3 if still no signal) |
| 2026-07-20 | Duplicate skill deletion (listen-wiseer + Parallax/sanyi) | workflow | `absence:duplicate-skill-names for 3 retros` | hypothesis — trending verified (2/3 retros) |
| 2026-07-22 | Worktree timing guidance in CLAUDE.md | friction | `absence:worktree-stale-state-error for 5 sessions` | hypothesis — trending verified (0 errors, 219 sessions) |
| 2026-07-22 | PR body `Closes #N` convention + quick-pr auto-gen | workflow | `absence:manual-issue-close for 5 sessions` | hypothesis — untestable (mixed evidence; graduate R3 if still no signal) |
| 2026-07-22 | Worktree agent commit convention in agile.md | safety | `absence:worktree-data-loss for 5 sessions` | hypothesis — trending verified (0 data loss) |
| 2026-07-24 | /dream Phase 8 independent tooling-change check | workflow | `absence:missed-retro-trigger for 3 tooling sessions` | hypothesis |
| 2026-07-24 | PULL_STRATEGY variable in Makefile.common | friction | `absence:rebase-conflict-abort for 5 sessions` | hypothesis |
| 2026-07-24 | Session intent classifier + compliance metric | observability | `ratio:execution-sessions-with-skills above 80%` | hypothesis |
| 2026-07-24 | FRICTION: label extraction + dashboard panel | observability | `presence:friction-label-in-insights` | hypothesis |
| 2026-07-24 | Agent spawn extraction + type attribution table | observability | `ratio:attributed-subagent-cost above 90%` | hypothesis |
| 2026-07-26 | Design skill description optimization (via skill-creator) | workflow | `presence:design-skill-invocation within 15 sessions` | hypothesis |
| 2026-07-26 | Hook telemetry wiring audit (hooks must call log_event) | observability | `count-drop:unique-hooks-in-log above 5 by R3` | hypothesis |
