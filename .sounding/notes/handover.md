# Handover — 2026-07-24 Cross-Repo Sweep + Makefile.common

**Context**: Operational session — merged 3 open PRs, synced 5 repos to main, fixed git LFS hooks, cleaned tracked pycache files, built and wired Makefile.common, updated workflow docs. Session closed with /dream synthesis (8 entries).

## Current State

### Completed this session
- **3 PRs merged**: listen-wiseer #75, ai-project-template #17, atlas #18
- **5 repos synced** to latest main (LAE, LIS, AIT, ATL, LIB)
- **Git LFS pre-push hook** fixed in atlas + librarian (`git init` re-applied template)
- **Makefile.common** (`~/.claude/Makefile.common`) created and `include`d in all 6 repos
- **Pycache cleanup**: guacamayo (17 files untracked, staged on GUA-23), atlas (PR #26 open)
- **Workflow order fix**: global CLAUDE.md updated — added bug/spike branch flow line
- **Synthesis**: 8 growth entries processed — see growth-log.md for dispositions

### Pending
- **Atlas PR #26** (ATL-22-remove-pycache) — ready to merge
- **Guacamayo pycache removal** — staged on `GUA-23-review-backbone`, ships with next commit
- **5 repos have uncommitted Makefile edits** (include line added, duplicates removed) — each needs branch/commit/PR per strict gates, or bundle into next planned work per repo

## Decisions Made
- Makefile.common uses `include ~/.claude/Makefile.common` — single source, repos keep own lint/test
- `REPO_NAME` auto-detected from `$(notdir $(CURDIR))` — no hardcoded names
- `ship` depends on repo-local `lint test` then common `pull push quick-pr`
- Bug/spike workflow added to CLAUDE.md as one-liner alongside the full pipeline

## Open Threads
- **Makefile PR strategy**: 5 repos need branches for the Makefile change. Options: individual `{PREFIX}-makefile-common` branches, or bundle into each repo's next planned work.
- **Dependabot workflow** (plan: `2026-07-22-dependabot-vuln-workflow.md`) — `make deps` + `deps-triage.sh` designed but not built.
- **Atlas Dependabot vuln alerts**: 2 high, 1 moderate — flagged on push, needs triage.

## Immediate Next Steps
1. Merge atlas PR #26 (pycache)
2. Decide Makefile PR strategy (batch vs. bundle)
3. Build `deps-triage.sh` + `make deps` (from dependabot plan doc)

## Key Files
- `~/.claude/Makefile.common` — the new shared include
- `~/.claude/CLAUDE.md:228` — bug/spike workflow line
- `.claude/docs/plans/2026-07-22-dependabot-vuln-workflow.md` — deps triage design
