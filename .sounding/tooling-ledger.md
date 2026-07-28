# Tooling Ledger — Active Experiments

Hypotheses under test. Verified/failed rows graduate to `tooling-ledger-log.md`.

**Metric types**: `absence:`, `count-drop:`, `presence:`, `ratio:`, `hook-blocks:`
**Area tags**: `cost` (token/model), `context` (compaction/window), `friction` (manual fixes/permissions), `quality` (review/lint/test), `workflow` (skills/pipeline/ceremony), `safety` (guards/gates), `observability` (telemetry/attribution)

---

| Date | Change | Area | Metric | Status |
|---|---|---|---|---|
| 2026-07-20 | growth-log.md + dream gate hook | workflow | `presence:growth-log rows >= cleared` | hypothesis — due 08-03 |
| 2026-07-24 | /dream Phase 8 independent tooling-change check | workflow | `absence:missed-retro-trigger for 3 tooling sessions` | hypothesis — trending verified (1/3) |
| 2026-07-24 | PULL_STRATEGY variable in Makefile.common | friction | `absence:rebase-conflict-abort for 5 sessions` | hypothesis — trending verified (0 events) |
| 2026-07-24 | Session intent classifier + compliance metric | observability | `ratio:execution-sessions-with-skills above 80%` | hypothesis — inconclusive (no compliance signals) |
| 2026-07-24 | FRICTION: label extraction + dashboard panel | observability | `presence:friction-label-in-insights` | hypothesis — failing (not present in insights-log 2026-07-27) |
| 2026-07-24 | Agent spawn extraction + type attribution table | observability | `ratio:attributed-subagent-cost above 90%` | hypothesis — failing (no signal in insights-log 2026-07-27) |
| 2026-07-26 | Design skill description optimization (via skill-creator) | workflow | `presence:design-skill-invocation within 15 sessions` | hypothesis — failing (0 invocations, 222 sessions) |
| 2026-07-27 | Remove bash_antipattern_warn.sh from settings+disk (F1) | friction | `absence:bash-antipattern-hook-in-settings after 1 retro` | hypothesis — approved, due 08-10 |
| 2026-07-27 | Investigate/change model default fable vs opus (F2) | cost | `ratio:fable-share above 25% within 5 sessions OR documented justification` | hypothesis — approved, due 08-10 |
| 2026-07-27 | lib.sh log_pass() for exit-0 hook visibility (F3) | observability | `count-drop:unique-hooks-in-pass-log above 5 within 2 retros` | hypothesis — approved, due 08-10 |
| 2026-07-27 | Plan-doc Status line enforcement (F6) | workflow | `absence:plan-doc-missing-status for 1 retro` | hypothesis — approved, due 08-10 |
