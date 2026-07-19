# Tooling Ledger

Every change to the tooling layer (hooks, skills, rules, settings) gets a row: what
changed, the friction that motivated it, and whether the fix actually took. `/retro`
reads this first — `hypothesis` rows are its top queue. Statuses: `hypothesis` (change
made, effect unproven) → `verified (evidence)` or `failed (evidence)`. Keep under ~1
screen: compress verified rows into monthly rollups.

## Experiment Tracking

Each `hypothesis` row carries a **Metric** — the observable signal that confirms or fails
the change. Metrics are machine-readable so `/insights` can check them against session data:

| Metric type | Format | Example |
|---|---|---|
| absence | `absence:<signal> for <N> sessions` | `absence:zsh-glob-abort for 3 sessions` |
| count-drop | `count-drop:<signal> from <N> to <M>` | `count-drop:permission-prompt from 5 to <2/session` |
| presence | `presence:<signal> within <N> sessions` | `presence:retrieval.jsonl rows within 5 sessions` |
| ratio | `ratio:<metric> <direction> <threshold>` | `ratio:>150k-context below 40%` |

`/insights` scans active hypotheses and reports: confirmed (metric met), trending (partial),
inconclusive (insufficient data), or failed (metric violated). `/retro` Step 0 uses these
verdicts to graduate or fail rows without re-deriving evidence manually.

---

| Date | Change | Motivating friction | Metric | Status |
|---|---|---|---|---|
| 2026-07 (rollup) | Settings Bash patterns (colon-form); /retro + ledger established; cartographer keyless + relinker anchor; /config-audit created; v2→v3 single-writer lifecycle proven (2 syntheses, capture-only confirmed); doc-artifact collapse (single dated plan doc, no SESSION.md); ledger relocated to guacamayo; /retro Step 5 apply-gated-on-approval (first end-to-end run 2026-07-18); akira global port (3 modes, eval-verified); commands/ retired (4+ sessions clean dispatch); wake-nudge hook (fires every session); model pairing codified (agents pinned per ref across sessions) | 14 items verified Jul 2026 — see git/session history for per-change detail | — | verified |
| 2026-07-17 (batch) | 12 infra changes awaiting specific trigger events: sanyi contract review, sync-global-skills detail output, zsh-gotchas (0 aborts), skill dedupe dispatch, librarian factual-record ingest, phase-protocol `repo:` scoping, rules→refs dispatch, review-sweep fresh-session akira-scan, review ladder L1-vs-L2 token comparison, retrieval telemetry accumulation, /compact-wiki first dry-run, repo-security-setup from ref. See git history 2026-07-17 for per-change detail | — | hypothesis (batch — verify individually on trigger) |
| 2026-07-17 | Session hygiene codified (global CLAUDE.md + models.md line): one work item per session, plan-doc as continuity, /execute in fresh sonnet session, meta sessions dispatch via 3-line spawn prompts into IDE sessions | /insights 7d: 66% of usage at >150k context, 12% on /execute in bloated sessions, terminal-spawned work invisible to Ramsey (wants IDE) | `ratio:>150k-context below 40%` | hypothesis — trending: 66%→58%→52% |
| 2026-07-17 | `.claude/docs/` git-ignored everywhere (Ramsey's call): `~/.gitignore_global` + core.excludesfile; untracked via `git rm --cached` in 6 repos | RISK: ledger/state/plans now have no git history; verify no lost-doc incident in 2 weeks | — | hypothesis — 2 days elapsed, no incident yet; verify at 2 weeks |
| 2026-07-18 | `~/.claude/hooks/memory_route_guard.sh` blocks writes to global auto-memory dir; redirects identity facts to guacamayo | Global memory protocol wrote identity facts silently | — | hypothesis — verify: next auto-memory write blocked + redirected |
| 2026-07-18 | shell.md gains deletion-safety rule (`git rm --cached` over `rm` for bulk ops) | Unrecoverable ledger loss from rm of git-ignored dir | — | hypothesis — verify: no destructive-rm incident in 3 sessions |
| 2026-07-19 | `~/.claude/hooks/task_complete_check.sh` (Stop hook): blocks completion until ruff lint+format pass on changed .py, tsc on .ts, pytest on src/ changes. Exit-status based (not output-string matching) | Claude finishing with lint errors or broken tests; user manually re-running after noticing | `absence:lint-errors-on-commit for 5 sessions` | hypothesis |
| 2026-07-19 | /grow skill broadened: prompts now scan 4 categories (identity, preferences/corrections, friction/gaps, what worked) — not just identity shifts | Process learnings and preference corrections evaporating between sessions; /grow only captured identity-level | `presence:non-identity-growth-entry within 3 sessions` | hypothesis |
| 2026-07-19 | Experiment tracking added to tooling ledger: Metric column + type vocabulary (absence/count-drop/presence/ratio); /insights gains experiment-check step; /retro Step 0 references metrics for verdict | Hypothesis verification was manual re-derivation with no connection to session data or dashboards | `presence:insights-experiment-verdict within 3 /insights runs` | hypothesis |
| 2026-07-19 | `~/.claude/rules/context-health.md` (always-on rule): compact at phase boundaries, before subagent spawns, after large reads, 30-turn heuristic | 52% of spend at >150k context; only 6 compacts across 98 sessions — compacting far too late | `ratio:>150k-context below 40%` | hypothesis |
| 2026-07-19 | `~/.claude/hooks/bash_antipattern_warn.sh` (PreToolUse Bash, advisory): warns when Bash used for cat/head/tail (→Read), grep/rg (→Grep), find/fd (→Glob). Allows pipes. Never blocks (exit 0) | 2,528 bash antipatterns (25.8/session); shell used where dedicated tools provide better context | `count-drop:bash-antipatterns from 25 to <10/session` | hypothesis |
| 2026-07-19 | `mcp-builder` moved `refs/` → `~/.claude/skills/` (20th global skill); CLAUDE.md skill inventory + refs line updated | Vendored Anthropic skill (SKILL.md frontmatter + scripts/) was filed as a ref, so nothing could trigger it — no `Refs:` line pointed at it and the Skill tool couldn't see it. Inert since added | `presence:mcp-builder-invoked within 3 MCP-building sessions` | hypothesis |
| 2026-07-19 | Ledger compressed: 3 items verified→rollup (commands-retired, wake-nudge, model-pairing), 12 legacy 2026-07-17 items batched into single hypothesis row | 21 hypothesis rows exceeded ~1 screen; retro Step 0 scanning cost | `absence:ledger-over-30-lines for 3 retros` | hypothesis |
