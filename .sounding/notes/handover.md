# Handover — 2026-07-17 Review Ladder + Model Pairing (evening)

**Context**: Sounding meta-layer session, continuation of the config-restructure day.
Arc: rules→refs → /review-sweep → review ladder (levels + workspace make) → model
pairing. First full v2 /synthesize ran mid-session. Everything below is uncommitted
across ~/.claude, ~/workspace/Makefile, guacamayo, listen-wiseer, ai-project-template.

## Current State

- **Identity**: /synthesize processed 5 growth entries → sounding.md gained
  subagent-provenance ("delegation doesn't transfer the verification duty") and
  cost-model-articulation weaves. growth.md cleared (0 entries). Single-writer design
  worked as intended first time (capture skills never touched seeds; mtime evidence
  for the v2 ledger row).
- **Review ladder EXECUTED** (`guacamayo/.claude/docs/plans/2026-07-17-workspace-review-ladder.md`):
  /review-sweep has `level:1|2|3` (+`headless` never-block → `### Needs input` section;
  hard rule: 3 levels, no sub-flags). Workspace `~/workspace/Makefile` ALREADY EXISTED
  (GROUP-scoped precommit/test/pull) — extended with help + review-fast/review/
  review-deep targets that PRINT the in-session command (Ramsey decided: no headless
  auto-run). Print forms + REPO-guard verified live.
- **Model pairing**: `~/.claude/refs/models.md` tiers every global skill + lifecycle
  skill + agent spawn (haiku fan-out pinned; /synthesize + /dream opus-always);
  pointer para in global CLAUDE.md; review-sweep step 4 restates haiku + verify-before-report.
- **listen-wiseer**: 3 sweep findings fixed (pipeline command names, Phase 8 → DONE,
  TodoWrite → TaskCreate|TaskUpdate matcher w/ input-logging jq — schema unverified,
  fails silent by construction). Resolution recorded in its sweep report.
- **Human-doc edits (Ramsey-directed, need her review before commit)**: guacamayo
  README "review ladder" section; ai-project-template README pointer line.

## Decisions Made

- Review order: sweep BEFORE commit; /code-review = plan-fidelity; /review-pr = post-PR.
- make judgment targets print, never auto-run (`claude -p` rejected for now).
- Sanyi architecture confirmed already-optimal: global skill + per-repo SANYI.md
  contracts; only `audit` is expensive → fenced at level:3 single-repo.
- Model principle: "pay for judgment, not for reading"; review ladder and model ladder
  are the same judgment-density axis. Guidance not enforcement — only agent-def
  frontmatter is mechanical.
- Reference tables live in refs/ (on-demand), never in the ledger (1-screen ceiling).

## Open Threads

- **Post-checkpoint arc (18:00+)**: /insights read → session hygiene codified (global
  CLAUDE.md: one item per session, fresh-sonnet /execute, spawn-prompt dispatch into
  IDE sessions; ledger row with measurable verify: next /insights >150k share <~40%).
  First spawn prompt drafted for the listen-wiseer sweep verification. Full account:
  reflection 2026-07-17_18-32.md.

- Ledger now carries ~4 fresh hypothesis rows from today (rules→refs, review-sweep,
  ladder, model pairing) — /retro's queue is deep; next retro is the big verification.
- Sweep acceptance criteria still unproven: fresh-session akira-scan named dispatch,
  seeded-bug catch on real code, SANYI severity mapping in a contract repo, L1
  zero-agent run, L3 sweep-refusal, L1-vs-L2 token comparison.
- Template render test for jinja folder stubs (`{{ ts_project_root }}` etc.) never run.
- Draft refs (langgraph.md, google-adk.md) still unreviewed by Ramsey.
- nonprofit-success-ai: no CLAUDE.md, Gemini key in Vite bundle — both wait on /scope-poc.

## Immediate Next Steps

1. Ramsey: review + commit the multi-repo uncommitted set (guacamayo README + template
   README with care — human docs); also standing: GitHub remote, delete puffin copy.
2. Fresh session: run sweep acceptance criteria (start `make review-fast REPO=listen-wiseer`
   → paste printed command; confirms akira-scan registration too).
3. Ramsey: review draft refs langgraph.md / google-adk.md.
4. Next /retro: work the hypothesis backlog (biggest queue yet).

## Key Files

- `~/.claude/refs/models.md`, `~/.claude/refs/` (all), `~/.claude/agents/akira-scan.md`
- `~/.claude/skills/review-sweep/SKILL.md`, `~/.claude/CLAUDE.md`
- `~/workspace/Makefile`
- `guacamayo/.claude/docs/plans/2026-07-17-{review-sweep,workspace-review-ladder}.md`
- `guacamayo/.claude/docs/tooling-ledger.md`
- `listen-wiseer/.claude/docs/plans/2026-07-17-review-sweep.md`
