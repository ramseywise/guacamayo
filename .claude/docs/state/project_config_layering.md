---
name: project-config-layering
description: Global ~/.claude is canonical for generic skills/hooks/commands; repo .claude is repo-specific only — dedup done 2026-07-16
metadata:
  node_type: memory
  type: project
  originSessionId: 09046113-8f02-4a31-96a3-9a981b951740
---

Config layering established 2026-07-16: `~/.claude` is the single source of truth for generic workflow
skills, commands, and guard hooks; repo `.claude/` dirs hold repo-specific assets only. Rule is documented
in `~/.claude/CLAUDE.md` § "Config Layering". `~/workspace/.claude` is a symlink to `~/.claude` (not a copy);
VSCode hides its runtime dirs via `~/workspace/.vscode/settings.json` `files.exclude`.

Dedup executed same day: deleted 19 duplicated skills from atlas, 9 from playground `skills/workflow/`,
3 playground commands, 6 stale guard hooks each from atlas/librarian/playground, and stripped duplicate
hook wiring from atlas/playground/listen-wiseer settings.json (double Stop notifications, double
secrets_scan, pip/rm guards). Repos keep `hooks/lib.sh` — project hooks source it. Global commands now
reference `~/.claude/skills/...` absolute paths so they work inside any repo. Deletions left uncommitted —
user commits ([[feedback-gitignore-over-delete]] checked: all were git-tracked).

**Why:** repo copies were stale (global versions newer: portable lib.sh sourcing, Claude-never-commits
guard) and caused double hook firing; atlas copies still contained legacy HC/VA client terms.

**How to apply:** never copy global assets into a repo; improve generic skills/hooks in `~/.claude` only.
Leftovers flagged: atlas `sprint-balance` skill still has HC terms ([[project-legacy-scrub]]); librarian
has unwired hooks (code_quality, sdk_lint, test_coverage, public_api_test_check not in its settings.json).

2026-07-17 second dedup pass (doc-collapse rollout): deleted atlas phase-skill copies
(research/plan/execute/review/pipeline/session_update/memory_audit) and playground `skills/global/`
(20 skills) — both were missed on 2026-07-16. Exception to the no-copies rule: `ai-project-template/template/.claude/skills/`
copies are INTENTIONAL (they seed team projects on machines without Ramsey's `~/.claude`) — keep them,
but keep their paths in sync with global convention changes. All deletions staged, uncommitted — Ramsey commits.
