# Handover — 2026-07-17 Rules→Refs Restructure + /review-sweep

**Context**: Sounding meta-layer session, first wake on the v2/guacamayo structure
(structure worked — seed load, wake nudge, relocated ledger all fired). Two work
arcs: config-layer restructure (always-on rules → on-demand refs) and building the
universal review capability.

## Current State

- **Rules→refs done**: `~/.claude/rules/` = always-on only (`docs.md`, new `shell.md`);
  stack conventions at `~/.claude/refs/` (python, typescript, logging, ml, adk-vercel,
  + NEW DRAFTS langgraph.md and google-adk.md — **Ramsey has not reviewed the drafts**).
  Dispatch = `Refs:` line in repo CLAUDE.md (atlas, listen-wiseer, playground,
  librarian, project-mgmt-ai) + folder-level nested CLAUDE.md stubs (atlas/web,
  playground/core, template `_scaffold/{{ ts_project_root }}`, `{{ eval_root }}`,
  `labs/`). Global CLAUDE.md Tooling section rewritten. Template render test NOT run.
- **`/review-sweep` built and first-run**: global skill + `~/.claude/agents/akira-scan.md`
  (first global agent def; replaces scaffolded akira as cross-repo mechanism). Plan with
  eval criteria: `guacamayo/.claude/docs/plans/2026-07-17-review-sweep.md` (EXECUTED).
  Live run on listen-wiseer (fast): lint PASS, 5 findings, report at
  `listen-wiseer/.claude/docs/plans/2026-07-17-review-sweep.md`.
- **Pending Ramsey approval**: 3 proposed fixes from that report — pipeline SKILL.md
  stale command names, settings.json:45 `TodoWrite` matcher, CLAUDE.md Phase 8 row.
  Not applied.
- growth.md at 4 entries (threshold 5) — newest: cost-model framing of config layers.
- Session runs on pre-restructure context; the refs slimming takes effect on restart.

## Decisions Made

- Config knowledge placed by **cost model**: always-on injection vs on-wake vs
  on-demand retrieval. Refs are deliberately NOT auto-loaded; repo CLAUDE.md `Refs:`
  line (repo default) + nested folder CLAUDE.md (deviations only) is the dispatch.
- Akira needs no repo scaffolding: global agent defs (`~/.claude/agents/`) are the
  dedup mechanism for cross-repo capabilities; scaffold akira stays a template-only
  feature. Its hardcoded-scan-roots blocker is moot for the sweep.
- `/review-sweep` is a sibling of `/code-review` (standing vs plan-fidelity), invokes
  sanyi when SANYI.md exists, delegates mechanical checks to each repo's Makefile.
- grant-fundraising-ai gets no refs (no code); nonprofit-success-ai has NO CLAUDE.md —
  folded into the queued /scope-poc work.

## Open Threads

- Mid-session limitation confirmed: newly created skills dispatch via command
  injection, but **agent defs register only at session start** — akira-scan named
  dispatch unverified (Explore fallback worked).
- Subagent scan produced one false positive (claimed `/plan review` was wrong);
  verifying agent claims against ground truth before reporting proved necessary —
  possible future rule for the skill.
- TodoWrite matcher find = settings-rot recurring in repo settings → supports periodic
  /config-audit cadence.
- Remaining sweep acceptance criteria: fresh-session akira-scan dispatch, seeded-bug
  catch on real code, SANYI severity mapping in a contract repo, `sweep` dirty-repo
  routing.
- Still unhoused: Gemini key exposure in nonprofit-success-ai vite.config.ts (needs a
  dssg plan-doc home via /scope-poc).

## Immediate Next Steps

1. Ramsey: approve/deny the 3 listen-wiseer fixes (report's Docs section).
2. Ramsey: review the two draft refs (langgraph.md, google-adk.md).
3. Fresh session: verify akira-scan agent dispatch + run remaining sweep acceptance
   criteria; template render test for the jinja folder stubs.
4. Ramsey (standing since v2): commit guacamayo diff, GitHub remote, delete puffin copy.

## Key Files

- `~/.claude/refs/` (all), `~/.claude/rules/{docs,shell}.md`, `~/.claude/agents/akira-scan.md`
- `~/.claude/skills/review-sweep/SKILL.md`
- `guacamayo/.claude/docs/plans/2026-07-17-review-sweep.md`
- `guacamayo/.claude/docs/tooling-ledger.md` (2 new hypothesis rows)
- `listen-wiseer/.claude/docs/plans/2026-07-17-review-sweep.md`
- `ai-project-template/template/CLAUDE.md.jinja` + `_scaffold/*/CLAUDE.md` stubs
