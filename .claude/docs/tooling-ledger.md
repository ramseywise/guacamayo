# Tooling Ledger

Tooling changes: `hypothesis` → `verified`/`failed`. `/retro` reads first; `/insights` checks metrics.
Metric types: `absence:`, `count-drop:`, `presence:`, `ratio:`, `hook-blocks:`. Keep under ~1 screen.

---

| Date | Change | Metric | Status |
|---|---|---|---|
| 2026-07 (rollup) | 20 verified/failed: Bash patterns, /retro+ledger, cartographer, v2→v3, doc-artifact, akira, commands/, wake-nudge, model pairing, git-ignore .claude/docs/, shell.md safety, /grow, experiment tracking. **Confirmed**: >150k context 66%→37%. **Failed**: bash_antipattern blocking (26.4 flat) | — | verified/failed |
| 2026-07-17 (batch) | 12 infra awaiting triggers: sanyi review, sync-global-skills, zsh-gotchas, skill dedupe, librarian ingest, phase-protocol, rules→refs, review-sweep, review ladder, retrieval telemetry, compact-wiki, repo-security | — | hypothesis (batch) |
| 2026-07-18 | memory_route_guard.sh | — | hypothesis |
| 2026-07-19 | task_complete_check.sh Stop hook | `absence:lint-errors-on-commit for 5 sessions` | hypothesis |
| 2026-07-19 | mcp-builder refs/→skills/ | `presence:mcp-builder-invoked within 3 MCP sessions` | hypothesis |
| 2026-07-19 | /docs-check + docs_drift_warn.sh | `presence:docs-check-finding within 3 L2 reviews` | hypothesis |
| 2026-07-20 | /sanyi init verify-before-write | `absence:contract-entry-with-zero-callsites for 2 inits` | hypothesis |
| 2026-07-20 | Plan-doc ABANDONED status | `presence:abandoned-status-used within 3 abandoned plans` | hypothesis |
| 2026-07-20 | Bash antipattern advisory→blocking | `count-drop:bash-antipatterns from 28 to <15` | hypothesis (deferred 1 window) |
| 2026-07-20 | Spawn model guidance + default→sonnet (2026-07-22) | `ratio:opus-share below 35%` | hypothesis |
| 2026-07-20 | Skill name mismatches fixed; typo aliases | `absence:skill-name-mismatch for 2 retros` | hypothesis |
| 2026-07-20 | Duplicate skill deletion (listen-wiseer + Parallax/sanyi 07-22) | `absence:duplicate-skill-names for 3 retros` | hypothesis |
| 2026-07-20 | growth-log.md + dream gate hook | `presence:growth-log rows >= cleared` | hypothesis — due 08-03 |
| 2026-07-20 | Hook telemetry (log_event, .hook-log.jsonl) | `hook-blocks:bash_antipattern_warn above 5/session` | hypothesis |
| 2026-07-20 | Design skill descriptions rewritten | `presence:design-skill-invocation within 10 sessions` | hypothesis |
| 2026-07-20 | sync-global-skills.sh guards | `absence:unaccounted-reservoir-skill for 3 retros` | hypothesis |
| 2026-07-20 | ci_drift_warn.sh advisory hook | `absence:broken-ci-path-on-main for 5 sessions` | hypothesis |
| 2026-07-20 | Parallax integration plan (5 phases) | `presence:review-shared-invoked within 3 L2+ reviews` | hypothesis — PLANNED |
| 2026-07-22 | Default model opus→sonnet in settings.json | `ratio:opus-share below 35%` | hypothesis |
| 2026-07-22 | Worktree timing guidance in CLAUDE.md | `absence:worktree-stale-state-error for 5 sessions` | hypothesis |
| 2026-07-22 | Ledger compressed 51→30 lines | `absence:ledger-over-30-lines for 3 retros` | hypothesis |
