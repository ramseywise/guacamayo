# Handover — 2026-08-11 Cross-repo cleanup + make prune + sisyphus rename

**Context**: Extended meta/housekeeping session after 4-day gap. Branch cleanup, sisyphus rename, interview-voice integration, galactus orientation, and new `make prune` automation.

## Current State

**Completed:**
- 17 local branches deleted across 6 repos (all merged or contained)
- job-system renamed to sisyphus (GitHub, local, prefix JOB→SIS, all config refs updated)
- interview-voice root files merged into sisyphus; interview-voice repo deleted
- galactus added to portfolio.md (Prototyping tier) + prefix table (GAL)
- wake/grow skill repo-lists updated with sisyphus + galactus
- `make prune` / `make prune-dry` added to workspace Makefile — cross-repo branch cleanup automation
  - Backs `~/.claude/scripts/prune.sh`: merged PRs (gh API), ancestor branches, tree-identical squash merges
  - Skips current branches with dirty state, skips dependabot
  - Dry-run showed 6 local + 57 remote branches to clean

**Uncommitted across repos:**
- guacamayo (`bug/friction-loop-capture-and-findings-pk`): dashboard, tooling-ledger, recurrence.py + tests, portfolio.md, wake/grow skills, growth.md, handover
- sisyphus (`JOB-33-ml6-genai-prototyping`): CLAUDE.md, pyproject.toml, .gitignore, Makefile, .env.example, src/ refs, coding-drill skill
- ~/.claude: CLAUDE.md prefix table, refs/agile.md prefix table, scripts/prune.sh
- ~/workspace/Makefile: prune targets

## Decisions Made

- sisyphus is the interview platform — drops "all Markdown, no runtime" constraint; gains voice drills
- galactus prefix = GAL, sisyphus prefix = SIS
- interview-voice absorbed, not kept as separate repo
- `make prune` is the answer to branch cleanup friction — Ramsey runs it directly, guard not involved
- Dependabot auto-merge correctly skips semver-major; GH Actions majors (low-risk) should get a separate policy
- AIT-64-scaffold-vscode-extensions: keep (issue #64 open, 1 commit ahead)

## Open Threads

- Galactus default branch is `spike/consolidate-claude-setup` — rename to `main` via gh API, then prune
- Sisyphus branch JOB-33 — rename to SIS-* or merge as bulk update
- GUA-98 (voice interview drill V1) should move to sisyphus board
- Sisyphus dependabot PRs #29, #30 (major GH Actions bumps) — merge manually
- Weekly retro overdue (last insights 08-04, last retro R8 08-05) — 7 days; insights refreshing in background
- Dependabot policy: consider auto-merging GH Actions majors separately from library majors
- Growth at 10 entries — synthesis due at /dream

## Immediate Next Steps

1. Run `make prune` from ~/workspace (after galactus branch rename)
2. Commit guacamayo changes (portfolio, skills, growth, dashboard, prune script)
3. Commit sisyphus changes (rename + voice integration)
4. Commit ~/.claude changes (prefix tables, prune script)
5. Run `/workflow-retro` (overdue)

## Key Files

- `~/.claude/scripts/prune.sh` (new — cross-repo branch cleanup)
- `~/workspace/Makefile:108-112` (prune targets)
- `~/.claude/CLAUDE.md:241` (prefix table)
- `~/.claude/refs/agile.md:20` (prefix table)
- `guacamayo/.sounding/portfolio.md:12` (galactus entry)
- `guacamayo/.claude/skills/wake/SKILL.md` (repo lists)
- `sisyphus/CLAUDE.md:1` (renamed)
- `sisyphus/pyproject.toml` (voice deps)
