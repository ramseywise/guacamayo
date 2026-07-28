# Tooling Ledger — Active Experiments

Hypotheses under test. Verified/failed rows graduate to `tooling-ledger-log.md`.

**Metric types**: `absence:`, `count-drop:`, `presence:`, `ratio:`, `hook-blocks:`
**Area tags**: `cost` (token/model), `context` (compaction/window), `friction` (manual fixes/permissions), `quality` (review/lint/test), `workflow` (skills/pipeline/ceremony), `safety` (guards/gates), `observability` (telemetry/attribution)

---

| Date | Change | Area | Metric | Status |
|---|---|---|---|---|
| 2026-07-20 | growth-log.md + dream gate hook | workflow | `presence:growth-log rows >= cleared` | hypothesis — due 08-03 |
| 2026-07-24 | /dream Phase 8 independent tooling-change check | workflow | `absence:missed-retro-trigger for 3 tooling sessions` | hypothesis — trending verified (2/3) |
| 2026-07-24 | Session intent classifier + compliance metric | observability | `ratio:execution-sessions-with-skills above 80%` | hypothesis — inconclusive (no compliance signals, 227 sessions) — due 08-10 |
| 2026-07-27 | lib.sh log_pass() for exit-0 hook visibility (F3) | observability | `count-drop:unique-hooks-in-pass-log above 5 within 2 retros` | hypothesis — 3 hooks wiring confirmed; signal pending — due 08-17 |
| 2026-07-27 | Plan-doc Status line enforcement (F6) | workflow | `absence:plan-doc-missing-status for 1 retro` | hypothesis — failing (2 docs missing Status at R4) |
| 2026-07-28 | TodoWrite hook for heavy sessions (>100 tool calls) | workflow | `ratio:TodoWrite-in-heavy-sessions above 50% by 2026-08-09` | hypothesis — R4 recommendation, due 08-17 |
| 2026-07-28 | Bash error stratification in cartographer (tool, error_type tuples) | observability | `presence:bash-stratified-taxonomy in insights by 2026-08-09` | hypothesis — R4 recommendation, due 08-17 |
| 2026-07-28 | Skill output verbosity cap (≤400 token budget in prompts) | workflow | `count-drop:p90-output-tokens below 700 by 2026-08-16` | hypothesis — R4 recommendation, due 08-24 |
| 2026-07-28 | Session breakpoint guidance for heavy sessions (>150k) | context | `ratio:top-session-cost-concentration below 40% by 2026-08-16` | hypothesis — R4 recommendation, due 08-24 |
| 2026-07-28 | Insights placement settled: engine+data in librarian, rendered artifacts in guacamayo/.sounding (report moved from .claude/docs/state) | observability | `absence:insights-artifacts-outside-sounding for 2 retros` | hypothesis — due 08-24 |
